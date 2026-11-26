@echo off
setlocal
cd /d "%~dp0"
echo ===============================================
echo        AGRISENSE AI - STARTUP
echo ===============================================
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python 3.12 virtual environment...
  py -3.12 -m venv .venv
  if errorlevel 1 (echo Python 3.12 was not found. Install Python 3.12 and try again. & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed. Check internet/Python version. pause & exit /b 1)
start "AgriSense Backend API" /D "%~dp0" cmd /k "call .venv\Scripts\activate.bat && uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 3 /nobreak >nul
start "AgriSense Frontend" /D "%~dp0" cmd /k "call .venv\Scripts\activate.bat && streamlit run frontend/app.py --server.port 8501"
timeout /t 5 /nobreak >nul
start http://localhost:8501
echo.
echo Frontend: http://localhost:8501
echo Backend:  http://127.0.0.1:8000/docs
echo Keep both terminal windows open.
