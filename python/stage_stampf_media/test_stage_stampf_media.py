import os
import tempfile
import unittest
from pathlib import Path
from stage_stampf_media import (
    sanitize_filename,
    generate_staged_name,
    validate_staging_safety,
    clean_staging_directory,
    create_staged_link,
    resolve_default_paths,
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

            # Should not raise for valid disjoint dirs
            validate_staging_safety(base, staging)

            # Should raise if base == staging
            with self.assertRaises(ValueError):
                validate_staging_safety(base, base)

            # Should raise if staging is parent of base
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

            # Test hardlink creation
            success, action = create_staged_link(src_file, dst_link, link_type="hardlink")
            self.assertTrue(success)
            self.assertEqual(action, "hardlink")
            self.assertTrue(dst_link.exists())
            self.assertTrue(dst_link.samefile(src_file))

            # Test idempotency
            success2, action2 = create_staged_link(src_file, dst_link, link_type="hardlink")
            self.assertTrue(success2)
            self.assertEqual(action2, "already_staged")

            # Test safe clean
            removed = clean_staging_directory(staging_photos)
            self.assertEqual(removed, 1)
            self.assertFalse(dst_link.exists())
            # Original file still exists intact
            self.assertTrue(src_file.exists())
            self.assertEqual(src_file.read_text(), "dummy photo data")

if __name__ == "__main__":
    unittest.main()
