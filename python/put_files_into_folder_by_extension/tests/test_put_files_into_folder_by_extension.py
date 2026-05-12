import unittest
from unittest.mock import patch
from pathlib import Path
import os
import sys

# Adjusting import path since the test is inside `tests/` subdirectory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from put_files_into_folder_by_extension import _unique_destination


class TestUniqueDestination(unittest.TestCase):

    @patch.object(Path, 'exists')
    def test_dest_does_not_exist(self, mock_exists):
        # Setup: destination does not exist
        mock_exists.return_value = False
        dest = Path("/fake/path/file.txt")

        # Execute
        result = _unique_destination(dest)

        # Verify
        self.assertEqual(result, dest)
        mock_exists.assert_called_once_with()

    @patch.object(Path, 'exists')
    def test_dest_exists_returns_1(self, mock_exists):
        # Setup: destination exists, but _1 does not
        # First call is for original dest, second is for candidate _1
        mock_exists.side_effect = [True, False]
        dest = Path("/fake/path/file.txt")

        # Execute
        result = _unique_destination(dest)

        # Verify
        expected = Path("/fake/path/file_1.txt")
        self.assertEqual(result, expected)
        self.assertEqual(mock_exists.call_count, 2)

    @patch.object(Path, 'exists')
    def test_multiple_existing_destinations(self, mock_exists):
        # Setup: original exists, _1 and _2 exist, _3 does not.
        # We will dynamically return True/False based on the path
        def mock_exists_side_effect():
            # If the path being checked is the original, _1, or _2, return True. Otherwise False.
            # We don't have access to 'self' easily here if we want to check the actual string,
            # but we can just use a side_effect function or a list.
            pass

        # The function checks:
        # original
        # _1
        # _2
        # _3
        mock_exists.side_effect = [True, True, True, False]
        dest = Path("/fake/path/file.txt")

        # Execute
        result = _unique_destination(dest)

        # Verify
        expected = Path("/fake/path/file_3.txt")
        self.assertEqual(result, expected)
        self.assertEqual(mock_exists.call_count, 4)

    @patch.object(Path, 'exists')
    def test_many_existing_destinations(self, mock_exists):
        # Test a case where many files exist to ensure loop/fast-path logic continues correctly
        # We'll make it so original and _1 through _11 exist, _12 does not.
        # This covers at least 13 calls.
        mock_exists.side_effect = [True] * 12 + [False]
        dest = Path("/fake/path/file.txt")

        # Execute
        result = _unique_destination(dest)

        # Verify
        expected = Path("/fake/path/file_12.txt")
        self.assertEqual(result, expected)
        self.assertEqual(mock_exists.call_count, 13)


if __name__ == '__main__':
    unittest.main()
