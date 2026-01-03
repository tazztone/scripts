@echo off
for %%i in (*) do (
 if not "%%~ni" == "organize" (
  md "%%~ni" && move "%%~i" "%%~ni"
 )
)