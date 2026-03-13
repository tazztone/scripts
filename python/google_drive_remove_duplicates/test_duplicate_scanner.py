import unittest
from unittest.mock import Mock
from duplicate_scanner import SelectionAssistant

class TestSelectionAssistant(unittest.TestCase):

    def setUp(self):
        # Mock service object (not directly used by SelectionAssistant for these tests, but required for init)
        self.mock_service = Mock()
        
        # Sample duplicate groups for testing
        self.duplicate_groups = {
            "md5_1": [
                {"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]},
                {"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]},
                {"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}
            ],
            "md5_2": [
                {"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]},
                {"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}
            ]
        }

    def test_mark_all_but_one_oldest(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='oldest')
        files_to_trash = assistant.get_files_to_trash()
        
        # For md5_1, 'file1_oldest' should be kept, others trashed
        self.assertIn({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)

        # For md5_2, 'file2_short' should be kept (older modifiedTime), 'file2_long' trashed
        self.assertIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)
        self.assertNotIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        
        self.assertEqual(len(files_to_trash), 3) # 2 from md5_1, 1 from md5_2

    def test_mark_all_but_one_newest(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='newest')
        files_to_trash = assistant.get_files_to_trash()

        # For md5_1, 'file1_newest' should be kept, others trashed
        self.assertIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_newest", "name": "b.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)

        # For md5_2, 'file2_long' should be kept (newer modifiedTime), 'file2_short' trashed
        self.assertIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertNotIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)

        self.assertEqual(len(files_to_trash), 3)

    def test_mark_all_but_one_smallest(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='smallest')
        files_to_trash = assistant.get_files_to_trash()

        # For md5_1, 'file1_oldest' (size 100) should be kept
        self.assertIn({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)

        # For md5_2, 'file2_long' (size 400) should be kept
        self.assertIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertNotIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)

        self.assertEqual(len(files_to_trash), 3)

    def test_mark_all_but_one_largest(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='largest')
        files_to_trash = assistant.get_files_to_trash()

        # For md5_1, 'file1_newest' (size 200) should be kept
        self.assertIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_newest", "name": "b.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)

        # For md5_2, 'file2_short' (size 500) should be kept
        self.assertIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)
        self.assertNotIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)

        self.assertEqual(len(files_to_trash), 3)

    def test_mark_all_but_one_shortest_name(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='shortest_name')
        files_to_trash = assistant.get_files_to_trash()

        # For md5_1, 'a.txt' (len 5) should be kept
        self.assertIn({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)

        # For md5_2, 'short.doc' (len 9) should be kept
        self.assertIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)
        self.assertNotIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)

        self.assertEqual(len(files_to_trash), 3)

    def test_mark_all_but_one_longest_name(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='longest_name')
        files_to_trash = assistant.get_files_to_trash()

        # For md5_1, 'c.txt' (len 5) should be kept (or b.txt, depends on sort stability for equal length)
        # Let's assume 'b.txt' is kept as it's the last in the sorted list if lengths are equal
        self.assertIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_newest", "name": "b.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)

        # For md5_2, 'very_long_name.doc' (len 18) should be kept
        self.assertIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertNotIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)

        self.assertEqual(len(files_to_trash), 3)

    def test_mark_by_folder(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_by_folder(folder_id_to_trash="folderA")
        files_to_trash = assistant.get_files_to_trash()

        # Files in folderA should be marked
        self.assertIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        
        # Files not in folderA should not be marked
        self.assertNotIn({"id": "file1_newest", "name": "b.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertNotIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertNotIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)

        self.assertEqual(len(files_to_trash), 2)

    def test_get_files_to_trash_uniqueness(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        
        # Mark the same file multiple times
        assistant.files_to_trash.append({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]})
        assistant.files_to_trash.append({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]})
        assistant.files_to_trash.append({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]})

        files_to_trash = assistant.get_files_to_trash()
        
        # Ensure only unique files are returned
        self.assertEqual(len(files_to_trash), 2)
        self.assertIn({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)

if __name__ == '__main__':
    unittest.main()
