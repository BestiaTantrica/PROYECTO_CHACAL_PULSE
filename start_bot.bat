@echo off
REM ============================================================================
REM CHACAL PULSE V4.1 - Script de Inicio del Bot
REM ============================================================================
REM Este script:
REM   1. Inicia los contenedores Docker de Freqtrade
REM   2. Verifica que la API esté respondiendo
REM   3. Envía notificación de "Sistema Activo" via Telegram
REM
REM Uso: start_bot.bat
REM ============================================================================

setlocal enabledelayedexpansion

REM Configuración
set "PROJECT_DIR=c:\ai_trading_agent\PROYECTO_CHACAL_PULSE"
set "LOG_FILE=%PROJECT_DIR%\logs\startup.log"
set "TELEGRAM_BOT_TOKEN=8733469976:AAHj8ZhIxRn0i9rNwau8ih8ygYoGbfYS6Ds"
set "TELEGRAM_CHAT_ID=6527908321"
set "FREQTRADE_API_URL=http://localhost:8080"
set "FREQTRADE_API_KEY=freqtrade"
set "FREQTRADE_API_PASS=chacal2026"

echo.============================================================
echo.  🦅 CHACAL PULSE V4.1 - INICIANDO SISTEMA
echo.============================================================
echo.

REM Crear directorio de logs si no existe
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"

REM Log de inicio
echo [%date% %time%] === INICIO SISTEMA CHACAL PULSE === >> "%LOG_FILE%"

echo [1/4] Iniciando contenedores Docker...
cd /d "%PROJECT_DIR%"
docker-compose up -d >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% neq 0 (
    echo ❌ ERROR: No se pudieron iniciar los contenedores Docker
    echo [%date% %time%] ERROR Docker >> "%LOG_FILE%"
    goto :error_docker
)

echo ✅ Contenedores iniciados

echo.
echo [2/4] Verificando API de Freqtrade...
set "API_OK=0"
set "ATTEMPT=0"

:wait_api
set /a ATTEMPT+=1
if %ATTEMPT% gtr 15 (
    echo ❌ ERROR: La API no responde después de 15 intentos
    echo [%date% %time%] ERROR API Timeout >> "%LOG_FILE%"
    goto :error_api
)

REM Intentar obtener balance de la API
curl -s -u %FREQTRADE_API_KEY%:%FREQTRADE_API_PASS% %FREQTRADE_API_URL%/api/v1/balance > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   Intentando... !ATTEMPT!/15
    timeout /t 2 /nobreak > nul
    goto :wait_api
)

set "API_OK=1"
echo ✅ API de Freqtrade respondiendo

echo.
echo [3/4] Verificando estado del bot...
curl -s -u %FREQTRADE_API_KEY%:%FREQTRADE_API_PASS% %FREQTRADE_API_URL%/api/v1/status > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ⚠️ Bot no está ejecutándose, iniciando...
    docker exec freqtrade freqtrade start --config config/config.json >> "%LOG_FILE%" 2>&1
    timeout /t 5 /nobreak > nul
)

echo ✅ Estado verificado

echo.
echo [4/4] Enviando notificación Telegram...
curl -s -X POST "https://api.telegram.org/bot%TELEGRAM_BOT_TOKEN%/sendMessage" ^
    -d "chat_id=%TELEGRAM_CHAT_ID%" ^
    -d "text=🦅 <b>CHACAL PULSE - SISTEMA ACTIVO</b>%0A%0A⏰ Hora: %date% %time%%0A%0A✅ Estado: Todos los servicios operativos%0A%0A🎯 Modo: Trading Automático%0A%0A---%0A<i>Chacal Pulse V4.1</i>" ^
    -d "parse_mode=HTML" > nul 2>&1

if %ERRORLEVEL% equ 0 (
    echo ✅ Notificación enviada
) else (
    echo ⚠️ Error al enviar notificación (no crítico)
)

echo.
echo.============================================================
echo.  ✅ SISTEMA CHACAL PULSE INICIADO CORRECTAMENTE
echo.============================================================
echo.

REM Log de éxito
echo [%date% %time%] === SISTEMA INICIADO OK === >> "%LOG_FILE%"

exit /b 0

:error_docker
echo.
echo.============================================================
echo.  ❌ ERROR EN DOCKER - VERIFICAR INSTALACIÓN
echo.============================================================
echo [%date% %time%] ERROR Docker >> "%LOG_FILE%"
exit /b 1

:error_api
echo.
echo.============================================================
echo.  ❌ ERROR API FREQTRADE - VERIFICAR SERVICIO
echo.============================================================
echo [%date% %time%] ERROR API >> "%LOG_FILE%"
exit /b 1