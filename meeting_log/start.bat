@echo off
REM Startup script for Meeting Minutes Service

echo ====================================
echo Meeting Minutes Service
echo ====================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and fill in your API keys.
    pause
    exit /b 1
)

REM Get Local IP Address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr "IPv4"') do set IP=%%a
set IP=%IP:~1%

REM Start Streamlit
echo Starting Streamlit server...
echo.
echo ============================================================
echo   Server is running! Access it via:
echo.
echo   [Local]   http://localhost:8501
echo   [Network] http://%IP%:8501  (Use this on your MacBook)
echo ============================================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM Auto-open browser to localhost
start http://localhost:8501

streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --browser.serverAddress=localhost
