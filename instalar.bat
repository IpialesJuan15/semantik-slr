@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe -m pip install -r requirements.lock
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip check
if errorlevel 1 goto error
echo Instalacion completa. Ejecuta iniciar.bat
exit /b 0
:error
echo La instalacion no termino. Revisa el mensaje anterior antes de continuar.
exit /b 1
