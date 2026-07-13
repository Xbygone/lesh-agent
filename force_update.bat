@echo off
title Lesh Agent Updater
echo =======================================
echo LESH AGENT - AUTO UPDATER
echo =======================================
echo.
echo En guncel surum GitHub'dan indiriliyor...

:: Eski temp dosyalarini temizle
if exist "lesh-agent.zip" del /q "lesh-agent.zip"
if exist "_temp_update_" rmdir /s /q "_temp_update_"

:: GitHub API'den en son sürümün ZIP adresini al ve indir
powershell -Command "$response = Invoke-RestMethod -Uri 'https://api.github.com/repos/Xbygone/lesh-agent/releases/latest'; $zipUrl = ($response.assets | Where-Object { $_.name -like '*.zip' }).browser_download_url; Invoke-WebRequest -Uri $zipUrl -OutFile 'lesh-agent.zip'"

if not exist "lesh-agent.zip" (
    echo [HATA] Guncelleme dosyasi indirilemedi!
    pause
    exit /b
)

echo.
echo Indirme tamamlandi. Dosyalar cikartiliyor...
powershell -Command "Expand-Archive -Path 'lesh-agent.zip' -DestinationPath '_temp_update_' -Force"

echo.
echo Yeni surum kuruluyor...
:: _temp_update_ icindeki klasoru bul
for /d %%I in ("_temp_update_\*") do (
    xcopy /s /e /y /q "%%I\*" "."
)

:: Temizlik
echo.
echo Gecici dosyalar temizleniyor...
rmdir /s /q "_temp_update_"
del /q "lesh-agent.zip"

echo.
echo Guncelleme basariyla tamamlandi!
echo Lesh Agent baslatiliyor...
timeout /t 2 /nobreak >nul

start lesh-agent.exe
