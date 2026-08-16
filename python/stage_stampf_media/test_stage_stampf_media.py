import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from stage_stampf_media import (
    sanitize_filename,
    generate_staged_name,
    validate_staging_safety,
    clean_staging_directory,
    create_staged_link,
    resolve_default_paths,
    fetch_immich_album_dates,
)

class TestStageStampfMedia(unittest.TestCase):

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("2021-01-01:Event*Name?"), "2021-01-01_Event_Name_")
        self.assertEqual(sanitize_filename("video<clip>|final.mp4"), "video_clip__final.mp4")
        self.assertEqual(sanitize_filename("  test..  "), "test")
        self.assertEqual(sanitize_filename(""), "unnamed")

    def test_generate_staged_name(self):
        root = Path("/tmp/events/2021-01-01")
        file1 = root / "sub" / "clip:1.mp4"
        name = generate_staged_name("2021-01-01_event", file1, root)
        self.assertEqual(name, "2021-01-01_event__sub__clip_1.mp4")

    def test_validate_staging_safety(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "base"
            staging = Path(tmpdir) / "staging"
            base.mkdir()
            staging.mkdir()

            # Disjoint paths should pass
            validate_staging_safety(base, staging)

            # Same paths should fail
            with self.assertRaises(ValueError):
                validate_staging_safety(base, base)

            # Staging being parent should fail
            with self.assertRaises(ValueError):
                validate_staging_safety(base, Path(tmpdir))

    def test_hardlink_creation_and_cleaning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "photos"
            staging = Path(tmpdir) / "staging"
            staging_photos = staging / "photos_raw"
            base.mkdir()
            staging_photos.mkdir(parents=True)

            src_file = base / "photo.dng"
            src_file.write_text("dummy photo data")

            dst_link = staging_photos / "event__photo.dng"

            # Hardlink creation
            success, action = create_staged_link(src_file, dst_link, link_type="hardlink")
            self.assertTrue(success)
            self.assertEqual(action, "hardlink")
            self.assertTrue(dst_link.exists())
            self.assertTrue(dst_link.samefile(src_file))

            # Idempotency
            success2, action2 = create_staged_link(src_file, dst_link, link_type="hardlink")
            self.assertTrue(success2)
            self.assertEqual(action2, "already_staged")

            # Safe clean
            removed = clean_staging_directory(staging_photos)
            self.assertEqual(removed, 1)
            self.assertFalse(dst_link.exists())
            self.assertTrue(src_file.exists())
            self.assertEqual(src_file.read_text(), "dummy photo data")

    @patch("urllib.request.urlopen")
    def test_fetch_immich_album_dates(self, mock_urlopen):
        mock_albums_response = MagicMock()
        mock_albums_response.read.return_value = json.dumps([
            {"id": "album-uuid-1", "albumName": "Stampf Hut"}
        ]).encode("utf-8")

        mock_album_details = MagicMock()
        mock_album_details.read.return_value = json.dumps({
            "id": "album-uuid-1",
            "albumName": "Stampf Hut",
            "assets": [
                {"id": "a1", "localDateTime": "2023-05-28T14:30:00.000Z"},
                {"id": "a2", "localDateTime": "2023-05-28T16:45:00.000Z"},
                {"id": "a3", "localDateTime": "2024-03-29T10:15:00.000Z"},
            ]
        }).encode("utf-8")

        # mock first call for /api/albums, second for /api/albums/id
        mock_urlopen.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_albums_response)),
            MagicMock(__enter__=MagicMock(return_value=mock_album_details)),
        ]

        name, dates = fetch_immich_album_dates("Stampf", "http://localhost:2283", "test-key")
        self.assertEqual(name, "Stampf Hut")
        self.assertEqual(dates, ["2023-05-28", "2024-03-29"])

if __name__ == "__main__":
    unittest.main()
