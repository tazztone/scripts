import unittest
from unittest.mock import Mock
from duplicate_scanner import SelectionAssistant

class TestSelectionAssistant(unittest.TestCase):

    def setUp(self):
        self.mock_service = Mock()

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
        self.assertIn({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)
        self.assertNotIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertEqual(len(files_to_trash), 3)

    def test_mark_all_but_one_newest(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='newest')
        files_to_trash = assistant.get_files_to_trash()
        self.assertIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_newest", "name": "b.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertNotIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)
        self.assertEqual(len(files_to_trash), 3)

    def test_mark_all_but_one_smallest(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='smallest')
        files_to_trash = assistant.get_files_to_trash()
        self.assertIn({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertNotIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)
        self.assertEqual(len(files_to_trash), 3)

    def test_mark_all_but_one_largest(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='largest')
        files_to_trash = assistant.get_files_to_trash()
        self.assertIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_newest", "name": "b.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)
        self.assertNotIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertEqual(len(files_to_trash), 3)

    def test_mark_all_but_one_shortest_name(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='shortest_name')
        files_to_trash = assistant.get_files_to_trash()
        self.assertIn({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)
        self.assertNotIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertEqual(len(files_to_trash), 3)

    def test_mark_all_but_one_longest_name(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_all_but_one(keep_strategy='longest_name')
        files_to_trash = assistant.get_files_to_trash()
        self.assertIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_newest", "name": "b.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertNotIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)
        self.assertEqual(len(files_to_trash), 3)

    def test_mark_by_folder(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.mark_by_folder(folder_id_to_trash="folderA")
        files_to_trash = assistant.get_files_to_trash()
        self.assertIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)
        self.assertIn({"id": "file1_middle", "name": "c.txt", "modifiedTime": "2023-01-01T11:00:00Z", "size": "150", "parents": ["folderA"]}, files_to_trash)
        self.assertNotIn({"id": "file1_newest", "name": "b.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertNotIn({"id": "file2_short", "name": "short.doc", "modifiedTime": "2023-03-01T10:00:00Z", "size": "500", "parents": ["folderC"]}, files_to_trash)
        self.assertNotIn({"id": "file2_long", "name": "very_long_name.doc", "modifiedTime": "2023-03-02T10:00:00Z", "size": "400", "parents": ["folderD"]}, files_to_trash)
        self.assertEqual(len(files_to_trash), 2)

    def test_get_files_to_trash_uniqueness(self):
        assistant = SelectionAssistant(self.mock_service, self.duplicate_groups)
        assistant.files_to_trash.append({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]})
        assistant.files_to_trash.append({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]})
        assistant.files_to_trash.append({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]})
        files_to_trash = assistant.get_files_to_trash()
        self.assertEqual(len(files_to_trash), 2)
        self.assertIn({"id": "file1_newest", "name": "b_longer_name.txt", "modifiedTime": "2023-01-02T10:00:00Z", "size": "200", "parents": ["folderB"]}, files_to_trash)
        self.assertIn({"id": "file1_oldest", "name": "a.txt", "modifiedTime": "2023-01-01T10:00:00Z", "size": "100", "parents": ["folderA"]}, files_to_trash)


class TestFetchAllFiles(unittest.TestCase):
    def test_fetch_all_files_http_error(self):
        from duplicate_scanner import fetch_all_files
        from googleapiclient.errors import HttpError
        import httplib2

        mock_service = Mock()
        mock_execute = Mock()
        mock_resp = httplib2.Response({'status': 500})
        mock_execute.side_effect = HttpError(resp=mock_resp, content=b'{"error": "Simulated error"}')
        mock_list = Mock()
        mock_list.execute = mock_execute
        mock_files = Mock()
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files

        result = fetch_all_files(mock_service)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
