@echo off
cd /d "%~dp0"
set "VERSION=1.5.1"
set "OLD_BROKEN_TAG=v1.5.0"
set "LOG=%~dp0publish_log.txt"
echo ==== Lesh Agent v%VERSION% publish - %date% %time% ==== > "%LOG%"
echo ============================================================
echo  Lesh Agent v%VERSION% - Publisher (log: publish_log.txt)
echo ============================================================

rem -- Read GITHUB_TOKEN from .env -----------------------------
set "TOKEN="
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
    if /i "%%a"=="GITHUB_TOKEN" set "TOKEN=%%b"
)
if not defined TOKEN (
    echo [ERROR] GITHUB_TOKEN not found in .env file.
    echo [ERROR] GITHUB_TOKEN not found in .env file. >> "%LOG%"
    pause
    exit /b 1
)
echo [OK] Token read from .env. >> "%LOG%"

rem -- Store token in Windows Credential Manager ---------------
> "%TEMP%\lesh_cred.txt" (
    echo url=https://github.com
    echo username=x-access-token
    echo password=%TOKEN%
    echo.
)
git credential approve < "%TEMP%\lesh_cred.txt" >> "%LOG%" 2>&1
del /q "%TEMP%\lesh_cred.txt" >nul 2>&1

set GIT_TERMINAL_PROMPT=0

rem -- 1/5: force push main ------------------------------------
echo [1/5] Pushing main branch...
echo [1/5] git push --force origin main >> "%LOG%"
git push --force origin main >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [WARN] Normal push failed, retrying with token URL... >> "%LOG%"
    git push --force "https://x-access-token:%TOKEN%@github.com/Xbygone/lesh-agent.git" main >> "%LOG%" 2>&1
)
if errorlevel 1 (
    echo [ERROR] main push failed. See publish_log.txt.
    type "%LOG%"
    pause
    exit /b 1
)
echo [OK] main pushed. >> "%LOG%"

rem -- 2/5: force push tags (old tags get rewritten) -----------
echo [2/5] Pushing tags...
echo [2/5] tag push >> "%LOG%"
git tag -d %OLD_BROKEN_TAG% >nul 2>&1
git push --force --prune origin "+refs/tags/*:refs/tags/*" >> "%LOG%" 2>&1
if errorlevel 1 (
    git push --force --prune "https://x-access-token:%TOKEN%@github.com/Xbygone/lesh-agent.git" "+refs/tags/*:refs/tags/*" >> "%LOG%" 2>&1
)
if errorlevel 1 (
    echo [WARN] Tag push may have partially failed, continuing... >> "%LOG%"
)

rem -- 3/5: dedicated build environment ------------------------
echo [3/5] Preparing isolated build environment (first run takes a few minutes)...
set "PY=python"
python --version >> "%LOG%" 2>&1
if errorlevel 1 set "PY=py -3"
%PY% --version >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install it from https://python.org
    echo [ERROR] Python not found. >> "%LOG%"
    pause
    exit /b 1
)

if not exist ".venv-build\Scripts\python.exe" (
    echo [3/5] Creating .venv-build... >> "%LOG%"
    %PY% -m venv .venv-build >> "%LOG%" 2>&1
)
set "VPY=%~dp0.venv-build\Scripts\python.exe"
if not exist "%VPY%" (
    echo [WARN] venv creation failed, falling back to system Python. >> "%LOG%"
    set "VPY=%PY%"
)
echo [3/5] Installing app dependencies + PyInstaller into build env... >> "%LOG%"
"%VPY%" -m pip install --disable-pip-version-check -q -r requirements.txt pyinstaller requests >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [ERROR] Dependency installation failed. See publish_log.txt.
    type "%LOG%"
    pause
    exit /b 1
)
"%VPY%" -c "import customtkinter, ollama, openai, supabase, cryptography, duckduckgo_search, bs4; print('[OK] All app dependencies importable in build env.')" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [ERROR] Build env is missing app dependencies. See publish_log.txt.
    type "%LOG%"
    pause
    exit /b 1
)

rem -- 4/5: build exe + publish GitHub Release -----------------
echo [4/5] Building exe and publishing Release v%VERSION% (takes a few minutes)...
echo [4/5] release.py %VERSION% >> "%LOG%"
"%VPY%" release.py %VERSION% >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [ERROR] Release step failed. See publish_log.txt.
    type "%LOG%"
    pause
    exit /b 1
)

rem -- 5/5: remove broken old release + verify -----------------
echo [5/5] Cleaning up broken %OLD_BROKEN_TAG% release and verifying...
"%VPY%" delete_release.py %OLD_BROKEN_TAG% >> "%LOG%" 2>&1
"%VPY%" verify_release.py >> "%LOG%" 2>&1
git ls-remote --heads origin main >> "%LOG%" 2>&1
echo [SUCCESS] All steps completed. >> "%LOG%"
echo.
echo ============================================================
echo  SUCCESS! Release: github.com/Xbygone/lesh-agent/releases
echo ============================================================
type "%LOG%"
pause
