@echo off
rem ==========================================================================
rem  Is Ilani Analizi - tek tikla baslatma (Windows)
rem  Ollama'yi CUDA kapali (Vulkan GPU) baslatir, modeli isitir, Streamlit'i acar.
rem  Ayarlar yalnizca bu pencereler icin gecerlidir; sistemde kalici bir sey degismez.
rem ==========================================================================
if "%~1"=="tarayici" goto tarayici
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title İş İlanı Analizi - Streamlit
set "MODEL=qwen2.5:7b"
set "PORT=8501"

echo.
echo  ================================================================
echo   İŞ İLANI ANALİZİ - başlatılıyor
echo  ================================================================
echo   KAPATMAK İÇİN: bu pencerede Ctrl+C'ye basın, "Toplu iş
echo   sonlandırılsın mı?" sorusuna H (Hayır) deyin; Ollama da kapanır.
echo   (Ya da bu pencereyi ve "Ollama (Vulkan GPU)" penceresini X ile kapatın.)
echo  ================================================================
echo.

rem --- Ollama'yi bul ---
set "OLLAMA=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not exist "%OLLAMA%" for /f "delims=" %%p in ('where ollama 2^>nul') do set "OLLAMA=%%p"
if not exist "%OLLAMA%" (
    echo [HATA] ollama.exe bulunamadı. https://ollama.com adresinden kurun.
    goto hata
)

rem --- Python'u bul (.venv varsa onu kullan) ---
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
"%PY%" -c "import streamlit, ollama" >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python veya paketler eksik. Şunu çalıştırın: pip install -r requirements-local.txt
    goto hata
)

rem --- 1) Tepsi uygulamasini ve calisan Ollama'yi kapat ---
echo [1/4] Ollama tepsi uygulaması ve eski Ollama süreçleri kapatılıyor...
taskkill /f /im "ollama app.exe" >nul 2>&1
taskkill /f /im ollama.exe >nul 2>&1
ping -n 3 127.0.0.1 >nul

rem --- 2) ollama serve: CUDA kapali, Vulkan acik (yalnizca bu oturum) ---
echo [2/4] Ollama başlatılıyor (CUDA kapalı, Vulkan GPU)...
set "CUDA_VISIBLE_DEVICES=-1"
set "OLLAMA_KEEP_ALIVE=30m"
start "Ollama (Vulkan GPU)" /min "%OLLAMA%" serve
set /a SAYAC=0
:ollama_bekle
curl -s -o nul http://127.0.0.1:11434/api/version && goto ollama_hazir
set /a SAYAC+=1
if %SAYAC% geq 30 (
    echo [HATA] Ollama 30 saniyede açılmadı. "Ollama (Vulkan GPU)" penceresine bakın.
    goto hata
)
ping -n 2 127.0.0.1 >nul
goto ollama_bekle
:ollama_hazir

rem --- 3) Modeli bir kez isit (GPU'ya yukle) ---
"%OLLAMA%" list | findstr /c:"%MODEL%" >nul
if errorlevel 1 (
    echo [UYARI] %MODEL% indirilmemiş. Şunu çalıştırın: ollama pull %MODEL%
) else (
    echo [3/4] %MODEL% ısıtılıyor ^(ilk açılışta 10-30 sn sürebilir^)...
    curl -s -o nul http://127.0.0.1:11434/api/generate -d "{\"model\":\"%MODEL%\",\"keep_alive\":\"30m\",\"options\":{\"num_ctx\":8192}}"
    echo       Model hazır.
)

rem --- 4) Streamlit; hazir olunca tarayiciyi ayri bir kucuk pencere acar ---
echo [4/4] Arayüz açılıyor: http://localhost:%PORT%
echo.
start "tarayici" /min cmd /c ""%~f0" tarayici %PORT%"
"%PY%" -m streamlit run app\app.py --server.headless true --server.port %PORT%

rem Streamlit kapandi -> Ollama'yi da kapat
echo.
echo Streamlit kapandı, Ollama durduruluyor...
taskkill /f /im ollama.exe >nul 2>&1
endlocal
exit /b 0

:hata
echo.
pause
exit /b 1

:tarayici
rem Streamlit cevap verene kadar (en fazla ~60 sn) bekle, sonra tarayiciyi ac
for /l %%i in (1,1,60) do (
    curl -s -o nul http://localhost:%2/_stcore/health && (start "" http://localhost:%2 & exit)
    ping -n 2 127.0.0.1 >nul
)
exit
