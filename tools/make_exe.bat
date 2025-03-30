@REM This uses pyinstaller to create a single binary executable. Adjust as needed for your system.

set SCRIPT_PATH=..\src\vrc_qr_scanner.py
set BUILD_PATH=..\bin\dist

"C:\Users\Gaming Computer\AppData\Local\Programs\Python\Python310\Scripts\pyinstaller.exe" --noconfirm --onefile "%SCRIPT_PATH%"

@REM cleanup post build
del vrc_qr_scanner.spec
rmdir /s /q build
xcopy /i /s /y /q dist ..\bin\dist 
rmdir /s /q dist

pause