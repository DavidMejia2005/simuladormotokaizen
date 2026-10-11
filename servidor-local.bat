@echo off
title Servidor Local - Simulador MotoKaizen (con cámara)
echo ========================================================
echo   Iniciando Servidor del Simulador MotoKaizen
echo   (Python + OpenCV: detección de rostro para biometría)
echo ========================================================
echo.
echo Abriendo en el navegador en http://localhost:5000 ...
echo Presiona Ctrl+C en esta ventana para detener el servidor.
echo.

:: Abrir navegador en la URL
start "" "http://localhost:5000"

:: Iniciar servidor del simulador (estáticos + /api/validate-face)
python "%~dp0servidor-simulador.py" 5000
pause
