@echo off
REM Usage: run.bat [install|backend|frontend|both]

set "ROOT=%~dp0"
cd /d "%ROOT%"

if "%1"=="" goto both
if /i "%1"=="install"  goto install
if /i "%1"=="backend"  goto backend
if /i "%1"=="frontend" goto frontend
if /i "%1"=="both"     goto both
goto usage

:install
echo Installing backend deps...
pip install -q -r backend\requirements.txt
echo Installing frontend deps...
pip install -q -r frontend\requirements.txt
goto end

:backend
echo Starting FastAPI backend on http://localhost:8000 ...
set "PYTHONPATH=%ROOT%"
python -m uvicorn backend.main:app --reload --port 8000
goto end

:frontend
echo Starting Streamlit frontend on http://localhost:8501 ...
set "PYTHONPATH=%ROOT%"
python -m streamlit run frontend\app.py --server.port 8501
goto end

:both
call :install
echo.
echo Starting both services (backend in background)...
set "PYTHONPATH=%ROOT%"
start "VINGEL-Backend" cmd /c "cd /d "%ROOT%" && set PYTHONPATH=%ROOT% && python -m uvicorn backend.main:app --port 8000 --reload"
python -m streamlit run frontend\app.py --server.port 8501
goto end

:usage
echo Usage: run.bat [install^|backend^|frontend^|both]
exit /b 1

:end
