import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

import sys
sys.path.insert(0, str(Path(__file__).parent))

import types
mock_exifread = types.ModuleType("exifread")
mock_exifread.process_file = lambda *args, **kwargs: {}
sys.modules["exifread"] = mock_exifread

from remove_jpg_if_raw_exists import is_valid_raw, read_exif, _check_exif

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
def test_check_exif_no_tags(mock_read_exif, tmp_path: Path):
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
