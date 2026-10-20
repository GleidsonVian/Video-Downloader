@echo off
rem Gera o "Downloader Pro.exe" nesta pasta a partir do main.py.
rem Rode sempre que mudar o codigo, ou quando o YouTube mudar algo e o
rem download parar de funcionar (ele atualiza o yt-dlp antes de empacotar).
title Recompilar Downloader Pro
cd /d "%~dp0"
rem "call": no pyenv o python e um .bat, e sem call o script pararia depois dele

echo === 1/3 Atualizando yt-dlp, python-vlc e PyInstaller...
call python -m pip install -U "yt-dlp[default]" python-vlc pyinstaller || goto erro

echo.
echo === 2/3 Gerando o executavel (leva uns 3 minutos)...
call python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "Downloader Pro" --icon icone.ico --add-data "icone.ico;." ^
    --collect-all yt_dlp --collect-all yt_dlp_ejs ^
    main.py || goto erro

echo.
echo === 3/3 Trocando pela versao nova...
rem O Windows nao deixa substituir um .exe aberto: fecha o programa antes
tasklist /FI "IMAGENAME eq Downloader Pro.exe" | find /I "Downloader Pro.exe" >nul
if not errorlevel 1 (
    echo.
    echo O Downloader Pro esta aberto e sera fechado para instalar a versao nova.
    echo Se tiver um download ou corte em andamento, espere terminar antes de continuar.
    pause
    taskkill /F /IM "Downloader Pro.exe" >nul 2>&1
    rem espera 2s o Windows liberar o arquivo
    ping -n 3 127.0.0.1 >nul
)
move /Y "dist\Downloader Pro.exe" "Downloader Pro.exe" >nul || goto erro_troca

rmdir /S /Q build dist 2>nul
del "Downloader Pro.spec" 2>nul

echo.
echo Pronto! O "Downloader Pro.exe" foi atualizado.
choice /M "Abrir o Downloader Pro agora"
if errorlevel 2 exit /b 0
start "" "Downloader Pro.exe"
exit /b 0

:erro_troca
echo.
echo Nao consegui trocar o executavel (o programa ainda esta aberto?).
echo A versao nova ficou em: dist\Downloader Pro.exe
echo Feche o Downloader Pro e rode este arquivo de novo.
pause
exit /b 1

:erro
echo.
echo Deu erro ao gerar o executavel. Veja a mensagem acima.
pause
exit /b 1
