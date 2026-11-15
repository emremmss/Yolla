@echo off
cd /d "%~dp0"
where python >nul 2>nul || (
    echo Python bulunamadi. https://www.python.org/downloads/ adresinden kur
    echo ve kurulumda "Add python.exe to PATH" kutusunu isaretle.
    pause
    exit /b 1
)
python -c "import qrcode" 2>nul || python -m pip install --quiet -r requirements.txt
python yolla.py %*
pause
