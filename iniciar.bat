@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ejecuta instalar.bat primero.
  exit /b 1
)
echo Abre http://127.0.0.1:8000 en tu navegador.
echo Para detener la aplicacion, pulsa Ctrl+C.
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
