# Semantik SLR

Primera entrega de una plataforma de vigilancia científica para revisiones sistemáticas vivas. Permite crear y consultar el protocolo de una revisión: título, pregunta de investigación y criterios de inclusión y exclusión. La interfaz está en español y se adapta a pantallas pequeñas. Los datos persisten en SQLite tras reiniciar la aplicación.

## Ejecutar en Windows

Requiere Git y Python. Desde la carpeta `semantik-slr` en la terminal de VS Code o Símbolo del sistema (`cmd`):

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Si `.venv` ya existe, comienza en el segundo comando. Abre `http://127.0.0.1:8000` en el navegador. Para detener el servidor, pulsa `Ctrl+C` en esa terminal. No hace falta activar el entorno virtual.

Para ejecutar las pruebas desde otra terminal en la misma carpeta:

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

## Organización

- `backend/app/main.py`: rutas, validación de formularios y persistencia de esta entrega.
- `frontend/templates/`: páginas HTML.
- `frontend/static/`: estilos.
- `tests/`: pruebas del flujo de creación y consulta.
- `requirements.txt`: dependencias directas de producción.
- `requirements-dev.txt`: dependencias directas para pruebas.
- `requirements.lock`: versiones exactas verificadas en Python 3.12. La instalación con Python 3.13 en Windows se comprobará al ejecutarla allí.

Los datos locales se guardan en `.local/reviews.sqlite3`, que Git ignora. Se puede elegir otra ruta mediante `SEMANTIK_DATABASE`.

La aplicación es un prototipo local para una persona. Aún no incluye acceso de usuarios, importación de revisión base, búsqueda académica, modelos de IA, actualización de artículos ni Zenodo. Los ejemplos de los formularios son orientativos y no representan un protocolo científico validado.
