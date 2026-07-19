@echo off
cd /d "%~dp0"
set "LOG=%~dp0publish_log.txt"
echo ==== Lesh Agent v1.5.0 publish - %date% %time% ==== > "%LOG%"
echo ============================================================
echo  Lesh Agent v1.5.0 - Yayinlama (log: publish_log.txt)
echo ============================================================

rem -- GITHUB_TOKEN'i .env'den oku -----------------------------
set "TOKEN="
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
    if /i "%%a"=="GITHUB_TOKEN" set "TOKEN=%%b"
)
if not defined TOKEN (
    echo [HATA] .env dosyasinda GITHUB_TOKEN bulunamadi.
    echo [HATA] .env dosyasinda GITHUB_TOKEN bulunamadi. >> "%LOG%"
    pause
    exit /b 1
)
echo [OK] Token .env'den okundu. >> "%LOG%"

rem -- Tokeni Windows Credential Manager'a kaydet --------------
> "%TEMP%\lesh_cred.txt" (
    echo url=https://github.com
    echo username=x-access-token
    echo password=%TOKEN%
    echo.
)
git credential approve < "%TEMP%\lesh_cred.txt" >> "%LOG%" 2>&1
del /q "%TEMP%\lesh_cred.txt" >nul 2>&1

set GIT_TERMINAL_PROMPT=0

rem -- 1/4: main dalini force push -----------------------------
echo [1/4] main dali push ediliyor...
echo [1/4] git push --force origin main >> "%LOG%"
git push --force origin main >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [UYARI] Normal push olmadi, token URL ile deneniyor... >> "%LOG%"
    git push --force "https://x-access-token:%TOKEN%@github.com/Xbygone/lesh-agent.git" main >> "%LOG%" 2>&1
)
if errorlevel 1 (
    echo [HATA] main push basarisiz. publish_log.txt dosyasina bakin.
    type "%LOG%"
    pause
    exit /b 1
)
echo [OK] main push edildi. >> "%LOG%"

rem -- 2/4: tag'leri force push (eski tag'ler yeniden yazilir) -
echo [2/4] Tag'ler push ediliyor...
echo [2/4] tag push >> "%LOG%"
git push --force --prune origin "+refs/tags/*:refs/tags/*" >> "%LOG%" 2>&1
if errorlevel 1 (
    git push --force --prune "https://x-access-token:%TOKEN%@github.com/Xbygone/lesh-agent.git" "+refs/tags/*:refs/tags/*" >> "%LOG%" 2>&1
)
if errorlevel 1 (
    echo [UYARI] Tag push kismen basarisiz olabilir, devam ediliyor... >> "%LOG%"
)

rem -- 3/4: Python + PyInstaller hazirla -----------------------
echo [3/4] Python / PyInstaller denetleniyor...
set "PY=python"
python --version >> "%LOG%" 2>&1
if errorlevel 1 set "PY=py -3"
%PY% --version >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi. https://python.org uzerinden kurun.
    echo [HATA] Python bulunamadi. >> "%LOG%"
    pause
    exit /b 1
)
%PY% -m pip install --disable-pip-version-check -q pyinstaller requests >> "%LOG%" 2>&1

rem -- 4/4: exe derle + GitHub Release v1.5.0 ------------------
echo [4/4] Exe derleniyor ve Release v1.5.0 yayinlaniyor (birkac dakika surebilir)...
echo [4/4] release.py 1.5.0 >> "%LOG%"
%PY% release.py 1.5.0 >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [HATA] Release adimi basarisiz. publish_log.txt dosyasina bakin.
    type "%LOG%"
    pause
    exit /b 1
)

rem -- Dogrulama -----------------------------------------------
git ls-remote --heads origin main >> "%LOG%" 2>&1
echo [BASARILI] Tum islemler tamamlandi. >> "%LOG%"
echo.
echo ============================================================
echo  BASARILI! Release: github.com/Xbygone/lesh-agent/releases
echo ============================================================
type "%LOG%"
pause
exit /b 0
