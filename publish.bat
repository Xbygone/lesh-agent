@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Lesh Agent v1.5.0 — Yayınlama Sihirbazı
echo ============================================================
echo.
echo  Bu script sırasıyla:
echo    1) Temizlenmiş git geçmişini GitHub'a FORCE PUSH eder
echo    2) Eski sızıntılı tag'leri yeniden yazar
echo    3) PyInstaller ile exe'yi derler
echo    4) GitHub Release v1.5.0'ı oluşturup zip'i yükler
echo.
echo  ÖNEMLİ: Devam etmeden önce GitHub PAT'ınızı iptal edip
echo  yenisini .env dosyasına yazdıysanız en iyisidir.
echo.
pause

echo.
echo [1/4] main dalı force push ediliyor...
git push --force origin main
if errorlevel 1 goto :error

echo.
echo [2/4] Tag'ler senkronize ediliyor (eski tag'ler yeniden yazilir)...
git push --force --prune origin "+refs/tags/*:refs/tags/*"
if errorlevel 1 echo [UYARI] Tag push kismen basarisiz olabilir, devam ediliyor...

echo.
echo [3/4] Yerel git copu temizleniyor...
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo.
echo [4/4] Exe derleniyor ve GitHub Release v1.5.0 yayinlaniyor...
python release.py 1.5.0
if errorlevel 1 goto :error

echo.
echo ============================================================
echo  ✔ TAMAMLANDI! Release: https://github.com/Xbygone/lesh-agent/releases
echo ============================================================
pause
exit /b 0

:error
echo.
echo [HATA] Islem basarisiz oldu. Yukaridaki ciktiyi kontrol edin.
pause
exit /b 1
