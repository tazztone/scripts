import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

import sys
sys.modules['exifread'] = MagicMock()
sys.path.insert(0, str(Path(__file__).parent))

import types
mock_exifread = types.ModuleType("exifread")
mock_exifread.process_file = lambda *args, **kwargs: {}
sys.modules["exifread"] = mock_exifread

from remove_jpg_if_raw_exists import (
    is_valid_raw,
    read_exif,
    _check_exif,
    parse_args,
    process_jpg,
    scan_and_remove,
    main,
)

# Tests for is_valid_raw
def test_is_valid_raw_success(tmp_path: Path):
    test_file = tmp_path / "test.raw"
    test_file.write_bytes(b"0" * 1024)
    assert is_valid_raw(test_file, min_size=500) == True
    assert is_valid_raw(test_file, min_size=1024) == True

def test_is_valid_raw_too_small(tmp_path: Path):
    test_file = tmp_path / "test.raw"
    test_file.write_bytes(b"0" * 1024)
    assert is_valid_raw(test_file, min_size=2048) == False

def test_is_valid_raw_missing_file(tmp_path: Path):
    missing_file = tmp_path / "missing.raw"
    assert is_valid_raw(missing_file, min_size=500) == False

@patch("pathlib.Path.stat")
def test_is_valid_raw_oserror(mock_stat, tmp_path: Path):
    mock_stat.side_effect = OSError("Mocked OSError")
    test_file = tmp_path / "test.raw"
    assert is_valid_raw(test_file, min_size=500) == False

# Tests for read_exif
def test_read_exif_missing_file(tmp_path: Path):
    missing_file = tmp_path / "missing.jpg"
    assert read_exif(missing_file) == {}

@patch("remove_jpg_if_raw_exists.exifread.process_file")
def test_read_exif_success(mock_process_file, tmp_path: Path):
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"dummy")

    expected_tags = {"Image Make": "Sony"}
    mock_process_file.return_value = expected_tags

    tags = read_exif(test_file)
    assert tags == expected_tags
    mock_process_file.assert_called_once()

@patch("remove_jpg_if_raw_exists.exifread.process_file")
def test_read_exif_exception(mock_process_file, tmp_path: Path):
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"dummy")
    mock_process_file.side_effect = Exception("corrupt file")
    tags = read_exif(test_file)
    assert tags == {}

# Tests for _check_exif
@patch("remove_jpg_if_raw_exists.read_exif")
def test_check_exif_empty_exif_tags(mock_read_exif, tmp_path: Path):
    mock_read_exif.return_value = {}
    jpg_path = tmp_path / "test.jpg"
    result, reason = _check_exif(jpg_path)
    assert result == False
    assert reason == "no EXIF data found"

@patch("remove_jpg_if_raw_exists.read_exif")
def test_check_exif_editor_software(mock_read_exif, tmp_path: Path):
    mock_read_exif.return_value = {
        "Image Software": "Adobe Photoshop 21.0"
    }
    jpg_path = tmp_path / "test.jpg"
    result, reason = _check_exif(jpg_path)
    assert result == False
    assert "editor software tag" in reason

@patch("remove_jpg_if_raw_exists.read_exif")
def test_check_exif_jfif_header(mock_read_exif, tmp_path: Path):
    mock_read_exif.return_value = {
        "JFIF JFIFVersion": "1.01"
    }
    jpg_path = tmp_path / "test.jpg"
    result, reason = _check_exif(jpg_path)
    assert result == False
    assert "JFIF header present" in reason

@patch("remove_jpg_if_raw_exists.read_exif")
def test_check_exif_no_makernotes(mock_read_exif, tmp_path: Path):
    mock_read_exif.return_value = {
        "Image Make": "Sony",
        "EXIF DateTimeOriginal": "2023:01:01 12:00:00"
    }
    jpg_path = tmp_path / "test.jpg"
    result, reason = _check_exif(jpg_path)
    assert result == False
    assert "no maker notes block" in reason

@patch("remove_jpg_if_raw_exists.read_exif")
def test_check_exif_missing_datetimeoriginal(mock_read_exif, tmp_path: Path):
    mock_read_exif.return_value = {
        "MakerNote": b"dummy_data",
        "Image Make": "Sony"
    }
    jpg_path = tmp_path / "test.jpg"
    result, reason = _check_exif(jpg_path)
    assert result == False
    assert "DateTimeOriginal missing" in reason

@patch("remove_jpg_if_raw_exists.read_exif")
def test_check_exif_happy_path(mock_read_exif, tmp_path: Path):
    mock_read_exif.return_value = {
        "MakerNote": b"dummy_data",
        "EXIF DateTimeOriginal": "2023:01:01 12:00:00",
        "Image Software": "Ver.1.00"
    }
    jpg_path = tmp_path / "test.jpg"
    result, reason = _check_exif(jpg_path)
    assert result == True
    assert "camera original" in reason


CAMERA_TAGS = {
    "MakerNote": b"dummy_data",
    "EXIF DateTimeOriginal": "2023:01:01 12:00:00",
}


def _args(**overrides):
    base = dict(
        dry_run=True, skip_exif=False, verbose=False,
        workers=2, min_raw_size=10,
    )
    base.update(overrides)
    return types.SimpleNamespace(**base)


# read_exif must see the full tag set: a stop_tag can hide the
# MakerNote/JFIF/Software tags the safety checks depend on.
@patch("remove_jpg_if_raw_exists.exifread.process_file")
def test_read_exif_no_stop_tag(mock_process_file, tmp_path: Path):
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"dummy")
    mock_process_file.return_value = {}
    read_exif(test_file)
    _, kwargs = mock_process_file.call_args
    assert "stop_tag" not in kwargs


def test_parse_args_rejects_zero_workers(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        sys, "argv", ["prog", str(tmp_path), "--workers", "0"])
    with pytest.raises(SystemExit):
        parse_args()


def test_parse_args_rejects_negative_min_raw_size(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        sys, "argv", ["prog", str(tmp_path), "--min-raw-size", "-1"])
    with pytest.raises(SystemExit):
        parse_args()


@patch("remove_jpg_if_raw_exists.read_exif")
def test_process_jpg_dry_run_keeps_file(mock_read_exif, tmp_path: Path, caplog):
    mock_read_exif.return_value = dict(CAMERA_TAGS)
    sub = tmp_path / "sub"
    sub.mkdir()
    jpg = sub / "IMG_0001.JPG"
    jpg.write_bytes(b"dummy")
    raw = sub / "IMG_0001.ARW"
    raw.write_bytes(b"0" * 64)
    with caplog.at_level("INFO"):
        result = process_jpg(jpg, raw, True, None, False, tmp_path)
    assert result == "deleted"
    assert jpg.exists()
    # Log must carry the relative path, not a bare basename
    assert "sub/IMG_0001.JPG" in caplog.text


@patch("remove_jpg_if_raw_exists.read_exif")
def test_process_jpg_keeps_editor_export(mock_read_exif, tmp_path: Path):
    mock_read_exif.return_value = {"Image Software": "Adobe Photoshop 21.0"}
    jpg = tmp_path / "IMG_0001.JPG"
    jpg.write_bytes(b"dummy")
    raw = tmp_path / "IMG_0001.ARW"
    raw.write_bytes(b"0" * 64)
    result = process_jpg(jpg, raw, False, None, False, tmp_path)
    assert result == "kept_edited"
    assert jpg.exists()


@patch("remove_jpg_if_raw_exists.read_exif")
def test_process_jpg_trash_preserves_tree(mock_read_exif, tmp_path: Path):
    mock_read_exif.return_value = dict(CAMERA_TAGS)
    sub = tmp_path / "sub"
    sub.mkdir()
    jpg = sub / "IMG_0001.JPG"
    jpg.write_bytes(b"dummy")
    raw = sub / "IMG_0001.ARW"
    raw.write_bytes(b"0" * 64)
    trash = tmp_path / "trash"
    result = process_jpg(jpg, raw, False, trash, False, tmp_path)
    assert result == "deleted"
    assert not jpg.exists()
    assert (trash / "sub" / "IMG_0001.JPG").exists()


@patch("remove_jpg_if_raw_exists.read_exif")
def test_process_jpg_trash_no_clobber(mock_read_exif, tmp_path: Path):
    mock_read_exif.return_value = dict(CAMERA_TAGS)
    jpg = tmp_path / "IMG_0001.JPG"
    jpg.write_bytes(b"dummy")
    raw = tmp_path / "IMG_0001.ARW"
    raw.write_bytes(b"0" * 64)
    trash = tmp_path / "trash"
    trash.mkdir()
    (trash / "IMG_0001.JPG").write_bytes(b"existing")
    result = process_jpg(jpg, raw, False, trash, False, tmp_path)
    assert result == "error"
    assert jpg.exists()
    assert (trash / "IMG_0001.JPG").read_bytes() == b"existing"


@patch("remove_jpg_if_raw_exists.read_exif")
def test_scan_and_remove_dry_run_end_to_end(mock_read_exif, tmp_path: Path, caplog):
    mock_read_exif.return_value = dict(CAMERA_TAGS)
    sub = tmp_path / "2026-01-01"
    sub.mkdir()
    # Uppercase JPG vs lowercase RAW exercises case-insensitive stem matching
    (sub / "DSC00001.JPG").write_bytes(b"dummy")
    (sub / "dsc00001.arw").write_bytes(b"0" * 64)
    (tmp_path / "orphan.JPG").write_bytes(b"dummy")
    with caplog.at_level("INFO"):
        scan_and_remove(tmp_path, None, _args())
    assert (sub / "DSC00001.JPG").exists()
    assert "Would remove" in caplog.text
    assert "No RAW match  : 1" in caplog.text


def test_main_rejects_trash_inside_scan_dir(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        sys, "argv",
        ["prog", str(tmp_path), "--trash", str(tmp_path / "trash-inside")])
    with pytest.raises(SystemExit):
        main()
