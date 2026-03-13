import os
import shutil

def organize_files_by_extension(folder_path):
    # Get a list of all files in the specified folder
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    # Create a dictionary to store files based on their extensions
    files_by_extension = {}

    # Organize files by extension
    for file in files:
        _, extension = os.path.splitext(file)
        extension = extension.lower()  # Convert the extension to lowercase for case-insensitivity

        if extension not in files_by_extension:
            files_by_extension[extension] = []

        files_by_extension[extension].append(file)

    # Create subfolders and move files accordingly
    for extension, file_list in files_by_extension.items():
        # Create a subfolder for each extension
        subfolder_path = os.path.join(folder_path, extension[1:])  # Remove the dot from the extension
        os.makedirs(subfolder_path, exist_ok=True)

        # Move files to their respective subfolders
        for file in file_list:
            current_file_path = os.path.join(folder_path, file)
            new_file_path = os.path.join(subfolder_path, file)

            # If a file with the same name already exists, add a suffix
            index = 1
            while os.path.exists(new_file_path):
                base_name, _ = os.path.splitext(file)
                new_file_path = os.path.join(subfolder_path, f"{base_name}_{index}{extension}")
                index += 1

            shutil.move(current_file_path, new_file_path)

    print("Organizing files completed.")

# Get the directory of the script
script_directory = os.path.dirname(__file__)

# Call the function to organize files
organize_files_by_extension(script_directory)
