# Semantik SLR

Primera entrega de una plataforma de vigilancia científica para revisiones sistemáticas vivas. Permite crear y consultar el protocolo de una revisión: título, pregunta de investigación y criterios de inclusión y exclusión. La interfaz está hecha con React, en español y adaptada a pantallas pequeñas. Los datos persisten en SQLite tras reiniciar la aplicación.

## Ejecutar en Windows

Requiere Git y Python. Desde la carpeta `semantik-slr` en la terminal de VS Code o Símbolo del sistema (`cmd`):

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Si `.venv` ya existe y las dependencias están instaladas, basta con el último comando. Abre `http://127.0.0.1:8000` en el navegador. Para detener el servidor, pulsa `Ctrl+C` en esa terminal. No hace falta activar el entorno virtual. La versión compilada de React se incluye para que puedas verla con Python, sin instalar Node.js todavía.

Para ejecutar las pruebas del backend desde otra terminal en la misma carpeta:

```bat
.venv\Scripts\python.exe -m pytest -q
```

## Ejecutar en Linux o el entorno en la nube

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

En la instancia de nube preparada, el entorno virtual también puede estar en `/workspace/.venvs/semantik-slr`. Usa su ejecutable `bin/python` con los mismos módulos desde la raíz del repositorio.

## Cambiar la interfaz React

Para editar React y generar una nueva versión de la página, instala Node.js LTS. Luego, desde la raíz del repositorio en Windows:

```bat
cd frontend
npm ci
npm run build
cd ..
```

Reinicia el servidor Python y actualiza el navegador. El backend ofrece los archivos compilados de `frontend/dist`. Durante el desarrollo de interfaz también puedes ejecutar `npm run dev` desde `frontend` en otra terminal y abrir la dirección que indique Vite. Sus peticiones `/api` se dirigen al backend en el puerto 8000.

## Organización

- `backend/app/main.py`: API JSON, validación y persistencia de esta entrega.
- `frontend/src/`: interfaz React y estilos.
- `frontend/dist/`: versión compilada que sirve Python.
- `frontend/templates/` y `frontend/static/`: interfaz inicial conservada como respaldo cuando no existe la compilación React.
- `tests/`: pruebas del flujo de creación y consulta.
- `requirements.txt`: dependencias directas de producción.
- `requirements-dev.txt`: dependencias directas para pruebas.
- `requirements.lock`: versiones exactas verificadas en Python 3.12. Se comprobó que los paquetes publicados incluyen versiones compatibles con Windows y Python 3.13; la instalación en ese equipo se comprueba al ejecutarla allí.
- `frontend/package-lock.json`: versiones exactas del frontend para `npm ci`.

Los datos locales se guardan en `.local/reviews.sqlite3`, que Git ignora. Se puede elegir otra ruta mediante `SEMANTIK_DATABASE`.

La aplicación es un prototipo local para una persona. Aún no incluye acceso de usuarios, importación de revisión base, búsqueda académica, modelos de IA, actualización de artículos ni Zenodo. Los ejemplos de los formularios son orientativos y no representan un protocolo científico validado.
