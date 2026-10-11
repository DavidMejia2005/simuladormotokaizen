@echo off
title Compartir simulador con tu celular - MotoKaizen
chcp 65001 >nul
setlocal

echo =============================================================
echo    COMPARTIR EL SIMULADOR MotoKaizen CON TU CELULAR
echo =============================================================
echo.

rem --- Obtener la IP local (Ethernet o WiFi) ---
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254*' -and $_.PrefixOrigin -ne 'WellKnown' } | Select-Object -First 1 -ExpandProperty IPAddress)"`) do set "IP=%%i"

if "%IP%"=="" (
    echo No se detecto una IP de red local.
    echo Conecta este computador a la MISMA red WiFi que usara tu celular.
    pause
    exit /b 1
)

set "URL=https://%IP%:5000"

rem --- Mostrar el enlace ---
echo  Abre esta direccion en el navegador de tu celular:
echo.
echo      %URL%
echo.
echo  (El celular debe estar conectado a la MISMA red WiFi.)
echo  La primera vez Safari mostrara un aviso por el certificado local.
echo  Pulsa Mostrar detalles ^> visitar este sitio para continuar.
echo.
echo  Abriendo el codigo QR para escanear con el celular...

rem --- Codigo QR escaneable + portapapeles ---
start "" "https://api.qrserver.com/v1/create-qr-code/?size=320x320&qzone=1&data=%URL%"
powershell -NoProfile -Command "Set-Clipboard -Value '%URL%'"

rem --- Si el servidor ya esta corriendo, no lo duplicamos ---
netstat -ano | findstr /C:":5000 " | findstr /I "LISTENING" >nul
if not errorlevel 1 (
    echo.
    echo  El servidor ya estaba activo en el puerto 5000.
    echo  El enlace tambien se copio al portapapeles.
    pause
    exit /b 0
)

echo.
echo  Iniciando el servidor (dejalo abierto para compartir)...
echo  Para detenerlo cierra esta ventana.
echo =============================================================
python "%~dp0servidor-simulador.py" 5000 0.0.0.0 --https
pause