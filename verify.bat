@echo off
cd /d "%~dp0"
git push origin main > verify_log.txt 2>&1
git rev-parse HEAD >> verify_log.txt 2>&1
set "PY=python"
if exist ".venv-build\Scripts\python.exe" set "PY=%~dp0.venv-build\Scripts\python.exe"
python --version >nul 2>&1
if errorlevel 1 if not exist ".venv-build\Scripts\python.exe" set "PY=py -3"
"%PY%" verify_release.py >> verify_log.txt 2>&1
type verify_log.txt
timeout /t 5 >nul
exit /b 0
