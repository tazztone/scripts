import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from categorize_organized_folders import categorize, _unique_destination, CATEGORIES

class TestCategorizeOrganizedFolders(unittest.TestCase):
    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.temp_dir_obj.name)

    def tearDown(self):
        self.temp_dir_obj.cleanup()

    def test_categorize_not_a_directory(self):
        file_path = self.temp_dir / "not_a_dir.txt"
        file_path.touch()
        with self.assertRaisesRegex(NotADirectoryError, "is not a directory"):
            categorize(file_path)

    def test_categorize_success(self):
        # Create extension directories
        jpg_dir = self.temp_dir / "jpg"
        jpg_dir.mkdir()
        pdf_dir = self.temp_dir / "pdf"
        pdf_dir.mkdir()

        # Create files
        (jpg_dir / "image1.jpg").touch()
        (jpg_dir / "image2.jpg").touch()
        (pdf_dir / "doc1.pdf").touch()

        summary = categorize(self.temp_dir)

        # Check files moved
        self.assertTrue((self.temp_dir / "Images" / "image1.jpg").exists())
        self.assertTrue((self.temp_dir / "Images" / "image2.jpg").exists())
        self.assertTrue((self.temp_dir / "Documents" / "doc1.pdf").exists())

        # Check extension folders are deleted
        self.assertFalse(jpg_dir.exists())
        self.assertFalse(pdf_dir.exists())

        # Check summary
        self.assertEqual(summary, {"Images": 1, "Documents": 1})

    def test_categorize_dry_run(self):
        jpg_dir = self.temp_dir / "jpg"
        jpg_dir.mkdir()
        (jpg_dir / "image1.jpg").touch()

        summary = categorize(self.temp_dir, dry_run=True)

        # Check file was NOT moved
        self.assertTrue((jpg_dir / "image1.jpg").exists())
        self.assertFalse((self.temp_dir / "Images" / "image1.jpg").exists())
        self.assertFalse((self.temp_dir / "Images").exists())

        # Check extension folder was NOT deleted
        self.assertTrue(jpg_dir.exists())

        # Check summary
        self.assertEqual(summary, {"Images": 1})

    def test_unique_destination(self):
        dest_dir = self.temp_dir / "dest"
        dest_dir.mkdir()

        target = dest_dir / "file.txt"

        # First file doesn't exist, should return same path
        res1 = _unique_destination(target)
        self.assertEqual(res1, target)

        # Create the first file
        target.touch()

        # Now it should append _1
        res2 = _unique_destination(target)
        self.assertEqual(res2, dest_dir / "file_1.txt")

        # Create the _1 file
        res2.touch()

        # Now it should append _2
        res3 = _unique_destination(target)
        self.assertEqual(res3, dest_dir / "file_2.txt")

    def test_categorize_empty_folder(self):
        # Create an empty extension folder
        jpg_dir = self.temp_dir / "jpg"
        jpg_dir.mkdir()

        summary = categorize(self.temp_dir)

        # Check folder was deleted
        self.assertFalse(jpg_dir.exists())

        # No category was created
        self.assertFalse((self.temp_dir / "Images").exists())

        # Summary shouldn't include it if there were no files
        self.assertEqual(summary, {})

    def test_categorize_conflict(self):
        # Create extension directories
        jpg_dir = self.temp_dir / "jpg"
        jpg_dir.mkdir()
        png_dir = self.temp_dir / "png"
        png_dir.mkdir()

        # Create files with same name
        (jpg_dir / "image.jpg").touch()
        (png_dir / "image.jpg").touch()

        summary = categorize(self.temp_dir)

        # Both files should be in Images, one renamed
        self.assertTrue((self.temp_dir / "Images" / "image.jpg").exists())
        self.assertTrue((self.temp_dir / "Images" / "image_1.jpg").exists())

        # Both dirs deleted
        self.assertFalse(jpg_dir.exists())
        self.assertFalse(png_dir.exists())

        # Summary should say 2 extension folders merged into Images
        self.assertEqual(summary, {"Images": 2})

if __name__ == '__main__':
    unittest.main()
