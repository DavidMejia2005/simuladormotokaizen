@echo off
title Simulador de Experiencia de Cliente - MotoKaizen
echo ========================================================
echo   Simulador MotoKaizen (modo archivo)
echo ========================================================
echo   Abre index.html directamente. NOTA: al abrir como
echo   archivo (file://) la camara no estara disponible;
echo   la biometria usara el modo simulado.
echo   Usa servidor-local.bat para la camara real.
echo ========================================================
echo Abriendo en tu navegador predeterminado...
start "" "%~dp0index.html"
exit
