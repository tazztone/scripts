# put-files-into-folder-according-to-file-extension
created with chatGPT 3.5
This Python script organizes files in a specified folder based on their file extensions. Here's a breakdown of what each part of the script does:

    Importing Modules:

    python

import os
import shutil

    os: Provides a way to interact with the operating system, such as listing files in a directory.
    shutil: Offers high-level file operations, such as moving files.

Function Definition: organize_files_by_extension

python

def organize_files_by_extension(folder_path):

    This function takes a folder_path as an argument, representing the path to the directory containing the files to be organized.

Listing Files in the Specified Folder:

python

files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    It uses a list comprehension to get a list of all files in the specified folder by checking if each item is a file (not a directory).

Creating a Dictionary to Organize Files by Extension:

python

files_by_extension = {}

    This dictionary will store files based on their extensions.

Organizing Files by Extension:

python

for file in files:
    _, extension = os.path.splitext(file)
    extension = extension.lower()  # Convert the extension to lowercase for case-insensitivity

    if extension not in files_by_extension:
        files_by_extension[extension] = []

    files_by_extension[extension].append(file)

    It iterates through the files, extracts the file extension (ignoring the filename itself), and organizes them into the files_by_extension dictionary.

Creating Subfolders and Moving Files:

python

for extension, file_list in files_by_extension.items():
    subfolder_path = os.path.join(folder_path, extension[1:])  # Remove the dot from the extension
    os.makedirs(subfolder_path, exist_ok=True)

    for file in file_list:
        current_file_path = os.path.join(folder_path, file)
        new_file_path = os.path.join(subfolder_path, file)

        index = 1
        while os.path.exists(new_file_path):
            base_name, _ = os.path.splitext(file)
            new_file_path = os.path.join(subfolder_path, f"{base_name}_{index}{extension}")
            index += 1

        shutil.move(current_file_path, new_file_path)

    It creates a subfolder for each unique extension, then moves the corresponding files into their respective subfolders.
    If a file with the same name already exists in the destination subfolder, it appends a suffix to the filename to avoid overwriting.

Printing Completion Message:

python

print("Organizing files completed.")

    It prints a message indicating that the file organization process is completed.

Getting the Directory of the Script:

python

script_directory = os.path.dirname(__file__)

    It gets the directory where the script is located using os.path.dirname(__file__).

Calling the Function with the Script Directory:

python

    organize_files_by_extension(script_directory)

        It calls the organize_files_by_extension function with the directory of the script, effectively organizing files in the same directory where the script is located.

