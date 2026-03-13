from __future__ import print_function
import os.path
import logging
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import sys

# Configure logging to write logs to a file and the console
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(filename='drive_scanner.log', level=logging.INFO, format=log_format)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format))
logging.getLogger().addHandler(console_handler)

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']


def get_service():
    """Authorize and return Google Drive service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds, cache_discovery=False)


from googleapiclient.errors import HttpError


class SelectionAssistant:
    def __init__(self, service, duplicate_groups):
        self.service = service
        self.duplicate_groups = duplicate_groups
        self.files_to_trash = []

    def mark_all_but_one(self, keep_strategy='oldest'):
        """Marks all but one file in each duplicate group for trashing."""
        logging.info(f"Applying 'mark all but one' strategy, keeping the {keep_strategy} file.")
        for md5, files in self.duplicate_groups.items():
            if len(files) > 1:
                # Sort files based on strategy to determine which one to keep
                if keep_strategy == 'oldest':
                    # Google Drive API does not directly provide creationTime in list, only modifiedTime
                    # For simplicity, we'll use modifiedTime for now, or assume the first one found is 'oldest'
                    # A more robust solution would require fetching creationTime for each file if needed.
                    # For now, let's just keep the first one in the list as a placeholder for 'oldest'
                    # or implement a proper sort if creationTime becomes available.
                    files_sorted = sorted(files, key=lambda x: x.get('modifiedTime', ''))
                elif keep_strategy == 'newest':
                    files_sorted = sorted(files, key=lambda x: x.get('modifiedTime', ''), reverse=True)
                elif keep_strategy == 'smallest':
                    files_sorted = sorted(files, key=lambda x: int(x.get('size', 0)))
                elif keep_strategy == 'largest':
                    files_sorted = sorted(files, key=lambda x: int(x.get('size', 0)), reverse=True)
                elif keep_strategy == 'shortest_name':
                    files_sorted = sorted(files, key=lambda x: len(x.get('name', '')))
                elif keep_strategy == 'longest_name':
                    files_sorted = sorted(files, key=lambda x: len(x.get('name', '')), reverse=True)
                else:
                    logging.warning(f"Unknown keep strategy: {keep_strategy}. Defaulting to keeping the first file.")
                    files_sorted = files

                # Keep the first file in the sorted list, trash the rest
                self.files_to_trash.extend(files_sorted[1:])
                logging.info(f"Marked {len(files_sorted) - 1} files for trashing in group {md5}.")

    def mark_by_folder(self, folder_id_to_trash):
        """Marks files for trashing if they are within the specified folder ID."""
        logging.info(f"Marking files in folder ID: {folder_id_to_trash} for trashing.")
        for md5, files in self.duplicate_groups.items():
            for file in files:
                if 'parents' in file and folder_id_to_trash in file['parents']:
                    self.files_to_trash.append(file)
                    logging.info(f"Marked file {file['name']} (ID: {file['id']}) in folder {folder_id_to_trash} for trashing.")

    def get_files_to_trash(self):
        """Returns the list of files marked for trashing."""
        # Remove duplicates from the list of files to trash (a file might be marked by multiple rules)
        unique_files_to_trash = []
        seen_ids = set()
        for file in self.files_to_trash:
            if file['id'] not in seen_ids:
                unique_files_to_trash.append(file)
                seen_ids.add(file['id'])
        return unique_files_to_trash


def move_file_to_trash(service, file):
    """Move the given file to trash."""
    try:
        service.files().update(fileId=file['id'], body={'trashed': True}).execute()
        logging.info(f"Successfully moved file {file['name']} (ID: {file['id']}) to trash.")
    except HttpError as error:
        logging.error(f"An error occurred while moving file {file['name']} (ID: {file['id']}) to trash: {error}")


def fetch_all_files(service, folder_id=None, recursive=False):
    """Fetch all file metadata from Google Drive."""
    
    if folder_id and recursive:
        logging.info("Starting recursive folder scan...")
        all_folder_ids = [folder_id]
        folders_to_process = [folder_id]
        while folders_to_process:
            current_folder_id = folders_to_process.pop(0)
            page_token = None
            while True:
                folder_query = f"'{current_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                response = service.files().list(q=folder_query, pageSize=1000, fields="nextPageToken, files(id, name)", pageToken=page_token).execute()
                subfolders = response.get('files', [])
                for folder in subfolders:
                    all_folder_ids.append(folder['id'])
                    folders_to_process.append(folder['id'])
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
        
        logging.info(f"Found {len(all_folder_ids)} total folders to scan.")
        
        all_files = []
        for i, f_id in enumerate(all_folder_ids, 1):
            page_token = None
            while True:
                file_query = f"'{f_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
                response = service.files().list(q=file_query, pageSize=1000, fields="nextPageToken, files(id, name, size, md5Checksum, trashed, parents)", pageToken=page_token).execute()
                all_files.extend(response.get('files', []))
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
            logging.info(f"Scanned folder {i} of {len(all_folder_ids)}. Total files found: {len(all_files)}")
        return all_files

    all_files = []
    page_token = None
    query = "mimeType != 'application/vnd.google-apps.folder' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    while True:
        response = service.files().list(
            q=query,
            pageSize=1000,
            fields="nextPageToken, files(id, name, size, md5Checksum, trashed, parents)",
            pageToken=page_token).execute()
        all_files.extend(response.get('files', []))
        logging.info(f"Retrieved {len(all_files)} file's metadata so far...")
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return all_files




def find_duplicates(service, delete=False, folder_id=None, recursive=False, keep_strategy=None, trash_folder_id=None):
    """Find duplicate files in Google Drive."""
    if folder_id:
        logging.info(f"Scanning folder with ID: {folder_id}")
    else:
        logging.info("Scanning all files in Google Drive.")
        
    all_files = fetch_all_files(service, folder_id, recursive)
    total_files = len(all_files)
    # Change: Store lists of files for each md5Checksum
    file_dict = {}
    for i, file in enumerate(all_files, 1):
        if 'md5Checksum' in file:
            md5 = file['md5Checksum']
            if md5 not in file_dict:
                file_dict[md5] = []
            file_dict[md5].append(file)

        if i % 100 == 0 or i == total_files:
            logging.info(f"Checked {i} out of {total_files} files.")

    # Filter out unique files, leaving only groups with duplicates
    duplicate_groups = {md5: files for md5, files in file_dict.items() if len(files) > 1}

    if not duplicate_groups:
        logging.info("No duplicate files found.")
        return

    logging.info(f"Found {len(duplicate_groups)} groups of duplicate files.")

    if not delete:
        logging.info("'--delete' flag was not used. No files will be moved to trash.")
        logging.info("Summary of duplicate files (not trashed):")
        for md5, files in duplicate_groups.items():
            logging.info(f"  MD5: {md5}")
            for file in files:
                logging.info(f"    - {file['name']} (ID: {file['id']})")
        return

    # Initialize SelectionAssistant
    selection_assistant = SelectionAssistant(service, duplicate_groups)

    # Apply selection strategies based on arguments
    if keep_strategy:
        selection_assistant.mark_all_but_one(keep_strategy)
    
    if trash_folder_id:
        selection_assistant.mark_by_folder(trash_folder_id)

    # Get the final list of files to trash
    files_to_trash = selection_assistant.get_files_to_trash()

    if files_to_trash:
        logging.info(f"Proceeding to trash {len(files_to_trash)} files based on selection criteria.")
        for file_to_trash in files_to_trash:
            move_file_to_trash(service, file_to_trash)
    else:
        logging.info("No files were marked for trashing based on the provided selection criteria.")



def main():
    parser = argparse.ArgumentParser(description="Find duplicate files in Google Drive")
    parser.add_argument('--delete', action='store_true', help='Move duplicate files to trash')
    parser.add_argument('--folder', help='ID of the Google Drive folder to scan')
    parser.add_argument('--recursive', action='store_true', help='Scan subfolders recursively when a folder is specified')
    parser.add_argument('--keep-strategy', choices=['oldest', 'newest', 'smallest', 'largest', 'shortest_name', 'longest_name'],
                        help='Strategy to keep one file in each duplicate group (e.g., oldest, newest, smallest, etc.). Implies --delete.')
    parser.add_argument('--trash-folder-id', help='ID of the folder from which to trash duplicate files. Implies --delete.')
    args = parser.parse_args()
    service = get_service()

    delete = args.delete or args.keep_strategy or args.trash_folder_id

    find_duplicates(service, delete=delete, folder_id=args.folder, recursive=args.recursive, 
                    keep_strategy=args.keep_strategy, trash_folder_id=args.trash_folder_id)


if __name__ == '__main__':
    main()


