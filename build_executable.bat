@echo off
rem Build CustomizMousee Windows executable
rem Ensure PyInstaller is installed: pip install pyinstaller
pyinstaller --onefile --noconsole --name CustomizMousee app.py
pause
