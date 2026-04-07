@echo off
echo 📦 NextGen SnowRunner Save Manager - Production Build
echo.

echo [1/2] Verifying PyInstaller...
pip install pyinstaller >nul 2>&1

echo [2/2] Compiling standalone executable via v111.00 Production Spec...
pyinstaller --noconfirm --clean snowrunner_editor.spec

echo.
echo ✅ Build Complete! 
echo Your new executable is located in the /dist folder.
pause
