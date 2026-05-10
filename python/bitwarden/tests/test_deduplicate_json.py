import unittest
import json
import os
import tempfile
import sys

# Add parent directory to sys.path to import deduplicate_json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from deduplicate_json import normalize_uri, deduplicate_bitwarden_export

class TestDeduplicateJson(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.TemporaryDirectory()
        self.input_file = os.path.join(self.test_dir.name, "input.json")
        self.output_file = os.path.join(self.test_dir.name, "output.json")
        self.summary_file = os.path.join(self.test_dir.name, "summary.md")

    def tearDown(self):
        # Cleanup temporary directory
        self.test_dir.cleanup()

    def write_json(self, filepath, data):
        with open(filepath, 'w') as f:
            json.dump(data, f)

    def read_json(self, filepath):
        with open(filepath, 'r') as f:
            return json.load(f)

    def test_normalize_uri(self):
        self.assertEqual(normalize_uri(""), "")
        self.assertEqual(normalize_uri(None), "")
        self.assertEqual(normalize_uri("HTTP://EXAMPLE.COM/"), "http://example.com")
        self.assertEqual(normalize_uri("  https://example.com/path  "), "https://example.com/path")
        self.assertEqual(normalize_uri("https://example.com//"), "https://example.com")

    def test_folders_deduplication(self):
        data = {
            "folders": [
                {"id": "id1", "name": "Work"},
                {"id": "id2", "name": "Work"},
                {"id": "id3", "name": "Personal"}
            ],
            "items": []
        }
        self.write_json(self.input_file, data)

        summary = deduplicate_bitwarden_export(self.input_file, self.output_file, quiet=True)

        output_data = self.read_json(self.output_file)
        self.assertEqual(len(output_data["folders"]), 2)

        folder_names = [f["name"] for f in output_data["folders"]]
        self.assertCountEqual(folder_names, ["Work", "Personal"])

        self.assertEqual(summary["original_folders"], 3)
        self.assertEqual(summary["deduplicated_folders"], 2)
        self.assertEqual(summary["removed_folders"], 1)

    def test_items_login_deduplication(self):
        data = {
            "folders": [],
            "items": [
                {
                    "id": "item1",
                    "type": 1,
                    "name": "My Login",
                    "login": {
                        "username": "user1",
                        "password": "password1",
                        "totp": "JBSWY3DPEHPK3PXP",
                        "uris": [{"uri": "http://example.com"}]
                    },
                    "notes": "Some notes"
                },
                {
                    "id": "item2",
                    "type": 1,
                    "name": "My Login",
                    "login": {
                        "username": "user1",
                        "password": "password1",
                        "totp": "JBSWY3DPEHPK3PXP",
                        "uris": [{"uri": "http://other-domain.com"}]
                    },
                    "notes": "Different notes"
                }
            ]
        }
        self.write_json(self.input_file, data)

        summary = deduplicate_bitwarden_export(self.input_file, self.output_file, quiet=True)

        output_data = self.read_json(self.output_file)
        self.assertEqual(len(output_data["items"]), 1)
        self.assertEqual(output_data["items"][0]["id"], "item1") # Should keep the first one

        self.assertEqual(summary["removed_items"], 1)

    def test_items_card_deduplication(self):
        data = {
            "folders": [],
            "items": [
                {
                    "id": "item1",
                    "type": 3,
                    "name": "My Card",
                    "card": {
                        "number": "1234567812345678",
                        "expMonth": "12",
                        "expYear": "2030"
                    }
                },
                {
                    "id": "item2",
                    "type": 3,
                    "name": "My Card",
                    "card": {
                        "number": "1234567812345678",
                        "expMonth": "12",
                        "expYear": "2030"
                    }
                }
            ]
        }
        self.write_json(self.input_file, data)

        deduplicate_bitwarden_export(self.input_file, self.output_file, quiet=True)

        output_data = self.read_json(self.output_file)
        self.assertEqual(len(output_data["items"]), 1)

    def test_items_different_login_not_deduplicated(self):
        data = {
            "folders": [],
            "items": [
                {
                    "id": "item1",
                    "type": 1,
                    "name": "My Login",
                    "login": {
                        "username": "user1",
                        "password": "password1",
                    }
                },
                {
                    "id": "item2",
                    "type": 1,
                    "name": "My Login",
                    "login": {
                        "username": "user2", # Different username
                        "password": "password1",
                    }
                },
                {
                    "id": "item3",
                    "type": 1,
                    "name": "My Login",
                    "login": {
                        "username": "user1",
                        "password": "different_password", # Different password
                    }
                }
            ]
        }
        self.write_json(self.input_file, data)

        deduplicate_bitwarden_export(self.input_file, self.output_file, quiet=True)

        output_data = self.read_json(self.output_file)
        self.assertEqual(len(output_data["items"]), 3)

    def test_folder_id_mapping(self):
        data = {
            "folders": [
                {"id": "folder_keep", "name": "Work"},
                {"id": "folder_remove", "name": "Work"}
            ],
            "items": [
                {
                    "id": "item1",
                    "type": 1,
                    "name": "Login 1",
                    "folderId": "folder_remove" # Uses the duplicate folder
                },
                {
                    "id": "item2",
                    "type": 1,
                    "name": "Login 2",
                    "folderId": "folder_keep" # Uses the kept folder
                }
            ]
        }
        self.write_json(self.input_file, data)

        deduplicate_bitwarden_export(self.input_file, self.output_file, quiet=True)

        output_data = self.read_json(self.output_file)

        self.assertEqual(len(output_data["folders"]), 1)
        self.assertEqual(output_data["folders"][0]["id"], "folder_keep")

        self.assertEqual(len(output_data["items"]), 2)
        # Both items should now reference the kept folder
        self.assertEqual(output_data["items"][0]["folderId"], "folder_keep")
        self.assertEqual(output_data["items"][1]["folderId"], "folder_keep")

    def test_summary_generation(self):
        data = {
            "folders": [
                {"id": "f1", "name": "F1"},
                {"id": "f2", "name": "F1"} # duplicate
            ],
            "items": [
                {"id": "i1", "type": 2, "name": "Note 1"},
                {"id": "i2", "type": 2, "name": "Note 1"} # duplicate
            ]
        }
        self.write_json(self.input_file, data)

        summary = deduplicate_bitwarden_export(self.input_file, self.output_file, self.summary_file, quiet=True)

        self.assertEqual(summary["original_folders"], 2)
        self.assertEqual(summary["deduplicated_folders"], 1)
        self.assertEqual(summary["removed_folders"], 1)

        self.assertEqual(summary["original_items"], 2)
        self.assertEqual(summary["deduplicated_items"], 1)
        self.assertEqual(summary["removed_items"], 1)

        # Verify summary file was created
        self.assertTrue(os.path.exists(self.summary_file))
        with open(self.summary_file, 'r') as f:
            content = f.read()
            self.assertIn("Items removed: 1", content)
            self.assertIn("Items kept: 1", content)

if __name__ == '__main__':
    unittest.main()
