@echo off
:: =================================================================================================
:: Script Name: windows_move_each_file_to_own_folder.bat
:: Description: Moves each file in the current directory into a new subfolder named after the file.
::              It skips a folder named "organize" if it exists.
:: Dependencies: None (standard Windows batch commands)
:: Usage: Run this script in the directory containing the files you want to enclose in folders.
:: =================================================================================================

for %%i in (*) do (
 if not "%%~ni" == "organize" (
  md "%%~ni" && move "%%~i" "%%~ni"
 )
)
