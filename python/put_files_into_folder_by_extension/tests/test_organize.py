import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Adjust import path to import from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from organize import (
    _unique_destination,
    load_config,
    organize_by_extension,
    categorize_folders,
    DEFAULT_CONFIG
)


class TestUniqueDestination(unittest.TestCase):

    @patch.object(Path, "exists")
    def test_dest_does_not_exist(self, mock_exists):
        mock_exists.return_value = False
        dest = Path("/fake/path/file.txt")
        result = _unique_destination(dest)
        self.assertEqual(result, dest)
        mock_exists.assert_called_once_with()

    @patch.object(Path, "exists")
    def test_dest_exists_returns_1(self, mock_exists):
        mock_exists.side_effect = [True, False]
        dest = Path("/fake/path/file.txt")
        result = _unique_destination(dest)
        expected = Path("/fake/path/file_1.txt")
        self.assertEqual(result, expected)
        self.assertEqual(mock_exists.call_count, 2)

    @patch.object(Path, "exists")
    def test_multiple_existing_destinations(self, mock_exists):
        mock_exists.side_effect = [True, True, True, False]
        dest = Path("/fake/path/file.txt")
        result = _unique_destination(dest)
        expected = Path("/fake/path/file_3.txt")
        self.assertEqual(result, expected)
        self.assertEqual(mock_exists.call_count, 4)


class TestConfigLoader(unittest.TestCase):

    @patch("pathlib.Path.is_file")
    def test_config_loader_missing_file_fallback(self, mock_is_file):
        mock_is_file.return_value = False
        config = load_config()
        self.assertEqual(config, DEFAULT_CONFIG)

    @patch("pathlib.Path.is_file")
    @patch("builtins.open")
    def test_config_loader_reads_valid_json(self, mock_open, mock_is_file):
        mock_is_file.return_value = True
        custom_config = {"skip_names": ["dummy.txt"], "categories": {"TestCat": ["ext"]}}
        
        # Setup mock file reading content
        mock_file = mock_open.return_value.__enter__.return_value
        mock_file.read.return_value = json.dumps(custom_config)
        
        config = load_config()
        self.assertEqual(config["skip_names"], ["dummy.txt"])
        self.assertEqual(config["categories"], {"TestCat": ["ext"]})


class TestOrganizeOperations(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_organize_by_extension_happy_path(self):
        # Create loose files
        (self.base_dir / "file1.txt").touch()
        (self.base_dir / "file2.jpg").touch()
        (self.base_dir / "noext").touch()

        # Run organize
        summary, _ = organize_by_extension(
            self.base_dir,
            skip_names={"organize.py"},
            no_ext_folder="no_extension",
            dry_run=False,
            recursive=False
        )

        self.assertEqual(summary, {"txt": 1, "jpg": 1, "no_extension": 1})
        self.assertTrue((self.base_dir / "txt" / "file1.txt").exists())
        self.assertTrue((self.base_dir / "jpg" / "file2.jpg").exists())
        self.assertTrue((self.base_dir / "no_extension" / "noext").exists())

    def test_organize_by_extension_dry_run(self):
        # Create loose file
        file_path = self.base_dir / "file1.txt"
        file_path.touch()

        # Run organize
        summary, _ = organize_by_extension(
            self.base_dir,
            skip_names=set(),
            no_ext_folder="no_extension",
            dry_run=True,
            recursive=False
        )

        self.assertEqual(summary, {"txt": 1})
        self.assertTrue(file_path.exists())
        self.assertFalse((self.base_dir / "txt").exists())

    def test_categorize_folders_happy_path(self):
        # Create extension subfolders
        txt_dir = self.base_dir / "txt"
        txt_dir.mkdir()
        (txt_dir / "doc.txt").touch()

        jpg_dir = self.base_dir / "jpg"
        jpg_dir.mkdir()
        (jpg_dir / "photo.jpg").touch()

        categories_map = {
            "Documents": ["txt"],
            "Images": ["jpg"]
        }

        # Run categorization
        cat_summary = categorize_folders(self.base_dir, categories_map, dry_run=False)

        self.assertEqual(cat_summary, {"Documents": 1, "Images": 1})
        self.assertTrue((self.base_dir / "Documents" / "doc.txt").exists())
        self.assertTrue((self.base_dir / "Images" / "photo.jpg").exists())
        self.assertFalse(txt_dir.exists())
        self.assertFalse(jpg_dir.exists())

    def test_recursive_organization(self):
        # Setup nested directories
        nested_dir = self.base_dir / "subdir"
        nested_dir.mkdir()
        (nested_dir / "nested.txt").touch()
        (self.base_dir / "root.txt").touch()

        # Run organize recursively
        summary, _ = organize_by_extension(
            self.base_dir,
            skip_names=set(),
            no_ext_folder="no_extension",
            dry_run=False,
            recursive=True
        )

        # nested.txt should move to txt/ nested.txt, root.txt to txt/ root.txt
        self.assertEqual(summary.get("txt"), 2)
        self.assertTrue((self.base_dir / "txt" / "root.txt").exists())
        # The unique index resolver handles collision if any, but names differ here
        self.assertTrue((self.base_dir / "txt" / "nested.txt").exists())

    def test_invalid_directory(self):
        # Setup: non-existent directory
        fake_path = self.base_dir / "does_not_exist"
        with self.assertRaises(NotADirectoryError):
            organize_by_extension(
                fake_path,
                skip_names=set(),
                no_ext_folder="no_extension",
                dry_run=False,
                recursive=False
            )

        # Setup: file path instead of directory
        file_path = self.base_dir / "regular_file.txt"
        file_path.touch()
        with self.assertRaises(NotADirectoryError):
            organize_by_extension(
                file_path,
                skip_names=set(),
                no_ext_folder="no_extension",
                dry_run=False,
                recursive=False
            )

    def test_skip_names_case_insensitivity(self):
        # Setup: file matching skip list but in uppercase
        (self.base_dir / "README.MD").touch()
        (self.base_dir / "Normal.txt").touch()

        summary, _ = organize_by_extension(
            self.base_dir,
            skip_names={"readme.md"},
            no_ext_folder="no_extension",
            dry_run=False,
            recursive=False
        )

        self.assertEqual(summary, {"txt": 1})
        self.assertTrue((self.base_dir / "README.MD").exists())
        self.assertTrue((self.base_dir / "txt" / "Normal.txt").exists())

    def test_name_collision_resolution(self):
        # Setup: Create folder 'txt' and a file 'file.txt' inside it.
        # Also create a loose 'file.txt' at root.
        txt_dir = self.base_dir / "txt"
        txt_dir.mkdir()
        (txt_dir / "file.txt").touch()
        (self.base_dir / "file.txt").touch()

        # Run organization
        summary, _ = organize_by_extension(
            self.base_dir,
            skip_names=set(),
            no_ext_folder="no_extension",
            dry_run=False,
            recursive=False
        )

        # Check file was renamed safely to file_1.txt
        self.assertEqual(summary, {"txt": 1})
        self.assertTrue((txt_dir / "file.txt").exists())
        self.assertTrue((txt_dir / "file_1.txt").exists())

    @patch.object(Path, "rmdir")
    def test_categorize_folders_empty_cleanup_safety(self, mock_rmdir):
        # Setup: mock rmdir to raise OSError (e.g., folder not empty or permissions error)
        mock_rmdir.side_effect = OSError("Mocked directory not empty")

        txt_dir = self.base_dir / "txt"
        txt_dir.mkdir()
        (txt_dir / "file.txt").touch()

        categories_map = {"Documents": ["txt"]}
        cat_summary = categorize_folders(self.base_dir, categories_map, dry_run=False)

        # Check it processed successfully
        self.assertEqual(cat_summary, {"Documents": 1})
        mock_rmdir.assert_called_once()


if __name__ == "__main__":
    unittest.main()
