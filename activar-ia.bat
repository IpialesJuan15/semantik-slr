@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ejecuta instalar.bat primero.
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements-ai.lock
if errorlevel 1 goto error
.venv\Scripts\python.exe -m backend.download_model
if errorlevel 1 goto error
echo Modelo listo. Reinicia la aplicacion y selecciona Similitud semantica.
exit /b 0
:error
echo No se pudo activar el modelo. La comparacion lexica sigue disponible.
exit /b 1
