import unittest
import tempfile
import os
from pathlib import Path

# Adjusting import path since the test is inside `tests/` subdirectory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from categorize_organized_folders import categorize, CATEGORIES

class TestCategorizeOrganizedFolders(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

        # Override CATEGORIES for testing to keep it fast and isolated
        # We'll use custom test categories and extensions
        self.original_categories = CATEGORIES.copy()
        CATEGORIES.clear()
        CATEGORIES.update({
            "Images": ["png", "jpg"],
            "Documents": ["pdf", "txt"]
        })

    def tearDown(self):
        CATEGORIES.clear()
        CATEGORIES.update(self.original_categories)
        self.temp_dir.cleanup()

    def test_categorize_happy_path(self):
        # Setup: Create extension folders with files
        png_dir = self.base_dir / "png"
        jpg_dir = self.base_dir / "jpg"
        pdf_dir = self.base_dir / "pdf"

        png_dir.mkdir()
        jpg_dir.mkdir()
        pdf_dir.mkdir()

        (png_dir / "file1.png").touch()
        (jpg_dir / "file2.jpg").touch()
        (pdf_dir / "doc.pdf").touch()

        # Execute
        summary = categorize(self.base_dir)

        # Verify
        self.assertEqual(summary, {"Images": 2, "Documents": 1})

        # Verify files are moved to category folders
        self.assertTrue((self.base_dir / "Images" / "file1.png").exists())
        self.assertTrue((self.base_dir / "Images" / "file2.jpg").exists())
        self.assertTrue((self.base_dir / "Documents" / "doc.pdf").exists())

        # Verify extension folders are removed
        self.assertFalse(png_dir.exists())
        self.assertFalse(jpg_dir.exists())
        self.assertFalse(pdf_dir.exists())

    def test_categorize_dry_run(self):
        # Setup
        png_dir = self.base_dir / "png"
        png_dir.mkdir()
        (png_dir / "file1.png").touch()

        # Execute
        summary = categorize(self.base_dir, dry_run=True)

        # Verify
        self.assertEqual(summary, {"Images": 1})

        # Verify no files were actually moved
        self.assertTrue((png_dir / "file1.png").exists())
        self.assertFalse((self.base_dir / "Images").exists())

    def test_categorize_not_a_directory(self):
        # Setup
        file_path = self.base_dir / "not_a_dir.txt"
        file_path.touch()

        # Execute & Verify
        with self.assertRaises(NotADirectoryError):
            categorize(file_path)

    def test_categorize_name_collision(self):
        # Setup: Two different extensions having a file with the same name
        png_dir = self.base_dir / "png"
        jpg_dir = self.base_dir / "jpg"

        png_dir.mkdir()
        jpg_dir.mkdir()

        (png_dir / "same_name").touch()
        (jpg_dir / "same_name").touch()

        # Execute
        summary = categorize(self.base_dir)

        # Verify
        self.assertEqual(summary, {"Images": 2})

        images_dir = self.base_dir / "Images"
        self.assertTrue((images_dir / "same_name").exists())
        self.assertTrue((images_dir / "same_name_1").exists() or (images_dir / "same_name_2").exists())

        self.assertFalse(png_dir.exists())
        self.assertFalse(jpg_dir.exists())

    def test_categorize_empty_folder_cleanup(self):
        # Setup: An empty extension folder
        png_dir = self.base_dir / "png"
        png_dir.mkdir()

        # Execute
        summary = categorize(self.base_dir)

        # Verify
        self.assertEqual(summary, {}) # No files moved, so nothing in summary
        self.assertFalse(png_dir.exists()) # But the empty folder should be removed

if __name__ == '__main__':
    unittest.main()
