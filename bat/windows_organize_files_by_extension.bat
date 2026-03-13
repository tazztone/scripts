@echo off
:: =================================================================================================
:: Script Name: windows_organize_files_by_extension.bat
:: Description: Moves all files in the current directory into subfolders named after their file extension.
::              Skips directories, .py files, and the script itself.
:: Dependencies: None (standard Windows batch commands)
:: Usage: Run this script in the directory you want to organize.
:: =================================================================================================

setlocal EnableExtensions EnableDelayedExpansion

rem Work in the script’s directory (non-recursive)
pushd "%~dp0" 2>nul

for %%F in (*) do (
  rem Skip directories
  if not exist "%%~fF\" (
    rem Skip .py files and this .bat
    if /I not "%%~xF"==".py" if /I not "%%~fF"=="%~f0" (

      rem Extension without dot; placeholder if none
      set "ext=%%~xF"
      if defined ext (
        set "ext=!ext:~1!"
      ) else (
        set "ext=_no_extension"
      )

      rem Create/use extension folder
      if not exist "!ext!\" md "!ext!" 2>nul

      rem Compute a unique destination (adds (n) if needed)
      call :UniqueDest target "!ext!" "%%~nF" "%%~xF"

      rem Move the file
      move /Y "%%~fF" "!target!" >nul
    )
  )
)

popd 2>nul
exit /b

:UniqueDest
rem %1=out var, %2=destdir, %3=base name, %4=ext (with dot or empty)
setlocal EnableDelayedExpansion
set "dest=%~2\%~3%~4"
set /a n=0
:ud_loop
if not exist "!dest!" (
  endlocal & set "%~1=%dest%" & exit /b
)
set /a n+=1
set "dest=%~2\%~3(!n!)%~4"
goto :ud_loop
