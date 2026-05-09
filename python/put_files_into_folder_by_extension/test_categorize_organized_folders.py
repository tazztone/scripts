import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from categorize_organized_folders import categorize, _unique_destination

class TestCategorizeOrganizedFolders(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_unique_destination_no_conflict(self):
        dest = self.folder / "file.txt"
        result = _unique_destination(dest)
        self.assertEqual(result, dest)

    def test_unique_destination_with_conflict(self):
        dest = self.folder / "file.txt"
        dest.touch()

        result = _unique_destination(dest)
        self.assertEqual(result, self.folder / "file_1.txt")

        result.touch()
        result2 = _unique_destination(dest)
        self.assertEqual(result2, self.folder / "file_2.txt")

    def test_categorize_not_a_directory(self):
        non_dir = self.folder / "not_a_dir.txt"
        non_dir.touch()

        with self.assertRaises(NotADirectoryError):
            categorize(non_dir)

    def test_categorize_basic(self):
        jpg_dir = self.folder / "jpg"
        jpg_dir.mkdir()
        (jpg_dir / "photo1.jpg").touch()
        (jpg_dir / "photo2.jpg").touch()

        png_dir = self.folder / "png"
        png_dir.mkdir()
        (png_dir / "image.png").touch()

        txt_dir = self.folder / "txt"
        txt_dir.mkdir()
        (txt_dir / "doc.txt").touch()

        summary = categorize(self.folder)

        self.assertEqual(summary, {"Images": 2, "Documents": 1})

        self.assertTrue((self.folder / "Images").is_dir())
        self.assertTrue((self.folder / "Images" / "photo1.jpg").exists())
        self.assertTrue((self.folder / "Images" / "photo2.jpg").exists())
        self.assertTrue((self.folder / "Images" / "image.png").exists())

        self.assertTrue((self.folder / "Documents").is_dir())
        self.assertTrue((self.folder / "Documents" / "doc.txt").exists())

        self.assertFalse(jpg_dir.exists())
        self.assertFalse(png_dir.exists())
        self.assertFalse(txt_dir.exists())

    def test_categorize_dry_run(self):
        jpg_dir = self.folder / "jpg"
        jpg_dir.mkdir()
        (jpg_dir / "photo1.jpg").touch()

        summary = categorize(self.folder, dry_run=True)

        self.assertEqual(summary, {"Images": 1})

        self.assertFalse((self.folder / "Images").exists())
        self.assertTrue(jpg_dir.exists())
        self.assertTrue((jpg_dir / "photo1.jpg").exists())

    def test_categorize_empty_folder(self):
        jpg_dir = self.folder / "jpg"
        jpg_dir.mkdir()

        summary = categorize(self.folder)

        self.assertNotIn("Images", summary)

        self.assertFalse(jpg_dir.exists())

    def test_categorize_rmdir_oserror(self):
        jpg_dir = self.folder / "jpg"
        jpg_dir.mkdir()
        (jpg_dir / "photo1.jpg").touch()

        with patch("pathlib.Path.rmdir") as mock_rmdir:
            mock_rmdir.side_effect = OSError("Directory not empty")
            summary = categorize(self.folder)

        self.assertEqual(summary, {"Images": 1})
        self.assertTrue((self.folder / "Images" / "photo1.jpg").exists())

if __name__ == '__main__':
    unittest.main()
