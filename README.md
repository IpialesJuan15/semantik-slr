# Semantik SLR · versión 0.9

Plataforma local de vigilancia científica para una tesis sobre actualización de revisiones sistemáticas vivas. Frontend React y backend FastAPI. Incluye gestión de protocolos, importación de revisión base, recuperación de artículos, análisis asistido, decisiones humanas, historial y reportes versionados.

## Ejecutar en Windows

Desde la carpeta del proyecto en CMD o la terminal de VS Code:

```bat
git fetch origin
git switch --track origin/feature/justificaciones-pdf-local
instalar.bat
iniciar.bat
```

Si la rama ya existe localmente, usa `git switch feature/justificaciones-pdf-local` y `git pull --ff-only`. Detén el servidor anterior con Ctrl+C antes de cambiar de rama. Si Git informa de cambios locales, consérvalos antes de continuar; no uses comandos que los borren. Si ya ejecutaste la versión 0.7 u 0.8, no necesitas repetir `instalar.bat`: no cambiaron las dependencias Python.

Abre `http://127.0.0.1:8000` en tu navegador local. Actualiza con Ctrl+F5 después de cambiar de versión. La compilación de React está incluida; Node.js solo es necesario para editar la interfaz. La base existente de `.local/reviews.sqlite3` se migra conservando las revisiones.

Se verificó la ejecución con Python 3.12 en Linux y la disponibilidad de paquetes para Windows de 64 bits con Python 3.13. La ejecución de los archivos BAT debe verificarse en Windows. Equipo objetivo: 8 GB de RAM, CPU; el modelo usa dos hilos y lotes pequeños. No se requiere GPU.

## Recorrido de la revisión publicada

1. En **Cargar revisión publicada**, elige el caso preparado de Salas-Pilco y Yang (2022), DOI `10.1186/s41239-022-00326-w`. Solo este DOI tiene hoy una ficha preparada; las revisiones manuales anteriores siguen disponibles.
2. Abre la revisión creada, adjunta su PDF original con texto seleccionable (hasta 8 MB/80 páginas) y coteja las preguntas, criterios, fuentes y fecha con el documento. La aplicación rechaza un PDF cuyo texto no contenga el DOI o título esperado.
3. Corrige lo necesario y pulsa **Confirmar método de la revisión**. No hay LLM ni extracción automática de criterios todavía: los valores son una transcripción inicial, atribuida al artículo, que requiere tu validación.
4. Explora los **31 estudios originales** de la tabla 1 y los recuentos de la tabla 2. Estos datos se guardan al crear la revisión y aparecen separados de los artículos nuevos. La tabla es una transcripción resumida; no contiene todavía el título completo, DOI y todos los campos de cada estudio original.
5. Pulsa **Buscar estudios posteriores**. Elige **OpenAlex** o **DOAJ** y un intervalo completo de fechas. La búsqueda empieza como mínimo el 1 de julio de 2021 y termina en la fecha que elijas, sin pasar de hoy. Un artículo de 2026 es válido si queda dentro del intervalo y cumple los demás criterios. DOAJ suele informar solo el año; confirma la fecha exacta de los artículos de los años límite. Ninguna de estas búsquedas reproduce las cuatro fuentes originales ni garantiza cobertura exhaustiva.
6. Genera un reporte. El JSON guarda el estudio base y los nuevos candidatos por separado; el HTML muestra DOI, recuentos originales y decisiones nuevas.

Los resultados tabulares **todavía no se actualizan automáticamente** al incluir un artículo. La siguiente fase incorporará extracción estructurada, confirmación de campos del nuevo estudio y cálculo de cambios de cada tabla.

La versión 0.7 hace visible la última búsqueda y cuántos resultados de la fuente quedaron sin recorrer. La lista de lectura muestra filtros con nombre, usa los años de la última búsqueda sin borrar candidatos y permite ir directamente a decisiones de un protocolo anterior. El expediente pone el resumen, las fuentes y la decisión a la vista; los fragmentos automáticos se abren cuando se necesiten y se describen como pistas, no como pruebas. En Informes se avisa antes de generar un borrador con decisiones pendientes. La biblioteca identifica cada proyecto por número y fecha para distinguir revisiones con el mismo título.

La versión 0.8 añadió **Texto completo** al expediente del candidato. **Buscar PDF abierto por DOI** consulta las ubicaciones abiertas de OpenAlex y prueba hasta cinco enlaces PDF; **Adjuntar PDF** permite incorporar uno obtenido por el investigador cuando no se puede descargar. El PDF se guarda localmente, con SHA-256, URL de procedencia cuando existe y texto extraído por página. El expediente muestra vistas previas y permite abrir el PDF guardado. Límite: 8 MB, 80 páginas y 160 000 caracteres extraídos. No hay OCR. Comprueba siempre que el PDF corresponde al candidato. El análisis semántico y los reportes aún trabajan con título/resumen y decisiones.

La versión 0.9 añade un **asistente experimental con LLM local** que examina pasajes seleccionados de todas las páginas extraídas y propone una explicación por criterio. Cada cita se comprueba contra la página declarada: si no aparece, se oculta la explicación y el criterio queda incierto. La presencia textual no valida la interpretación ni la elegibilidad. El investigador conserva la decisión final. Las propuestas se guardan con modelo, hash del PDF y versión del protocolo; quedan obsoletas si cambia cualquiera de los dos. El informe y la clasificación semántica anterior aún no usan estas propuestas. Se reparan en la presentación algunos glifos numéricos de PDFs, como `/one.tnum` → `1`.

Si una búsqueda antigua guardó la propia revisión base como candidato, el registro y su decisión se conservan como antecedente, pero ya no cuentan como estudio nuevo, no participan en nuevos análisis ni en la tabla CSV de candidatos. Un reporte nuevo conserva ese registro aparte en `legacy_base_records` del JSON. Mientras queden pendientes, el reporte se marca como **Borrador**. Los reportes anteriores siguen siendo instantáneas inmutables y conservan sus cifras históricas.

El estudio base se publicó en **2022**, pero examinó estudios publicados **hasta el 30 de junio de 2021**. Sus 31 estudios originales aparecen como antecedentes; no son nuevos candidatos. La propia revisión de 2022 tampoco es un estudio primario nuevo y ahora se omite en búsquedas/importaciones futuras. Si ya la tenías guardada como candidato, la aplicación la señala para que revises y corrijas su decisión; no borra automáticamente tus datos ni tu historial.

El filtro de fechas de **Buscar más estudios** se aplica a la siguiente consulta, no elimina artículos recuperados antes. La lista de lectura permite ver **todas las fechas guardadas** o limitarse a los **años del intervalo seleccionado**. El filtro de la lista usa años porque DOAJ no siempre ofrece día y mes.

## Después de recuperar artículos en DOAJ

1. En **Buscar y decidir**, la guía **Siguiente paso** indica qué falta. Si ya hay candidatos, elige **Analizar artículos** en la misma pantalla. Puedes empezar con **TF-IDF**; si activaste el modelo local, usa **Similitud semántica**.
2. Pulsa **Revisar el siguiente**. La lista de lectura y el detalle aparecen juntos en escritorio. En móvil, al elegir un candidato se abre su detalle más abajo.
3. Comprueba título, resumen, DOI/enlace y fragmentos contra los criterios de la revisión. El puntaje solo ordena la lectura: no decide por ti. Si el artículo es del primer o último año del intervalo, confirma su fecha exacta en la fuente.
   En **Texto completo**, pulsa **Buscar PDF abierto por DOI**. Si falla, abre la fuente y usa **Adjuntar PDF** cuando dispongas de una copia autorizada. Verifica título y DOI en el PDF; el estado «PDF leído» solo acredita extracción de texto, no elegibilidad.
   Tras activar Ollama, pulsa **Generar propuestas con LLM local**. Abre el PDF y coteja la página, la cita y la interpretación de cada criterio antes de guardar tu propia decisión.
4. Selecciona **Incluido**, **Excluido** o **Pendiente**, escribe el motivo y pulsa **Guardar decisión**. La aplicación abre el siguiente candidato pendiente cuando corresponde.
5. Cuando termines, abre **Informes** y genera una versión. Para añadir más candidatos, usa **Buscar más estudios** en la misma pantalla. No necesitas crear otra revisión ni volver a cargar el PDF.

La skill [Interface Design](.agents/skills/interface-design/SKILL.md) se instaló en el proyecto desde [Dammyjay93/interface-design](https://github.com/Dammyjay93/interface-design), commit `2f9be3206855bcb2d1d0af262c8bae25cba6658d`, bajo licencia MIT. Está incluida para Codex en `.agents/skills` y para Claude Code en `.claude/skills`, sin requerir una instalación global. Los patrones propios de esta aplicación están en `.interface-design/system.md`. El comando `/plugin marketplace add` pertenece a Claude Code y se puede usar allí si también quieres instalar su plugin globalmente.

## Activar el modelo semántico

```bat
activar-ia.bat
```

Instala FastEmbed/ONNX Runtime y descarga el modelo multilingüe y su tokenizador (aproximadamente 252 MB, además de las dependencias). Usa la conexión a Hugging Face y sus servidores de descarga, incluido `us.aws.cdn.hf.co`. La descarga es local a `.local/models`; el modelo no se envía al repositorio. Se fija la revisión del modelo y se verifican SHA-256 de los pesos y del tokenizador. Reinicia el servidor después de activarlo.

Mientras no esté descargado, la comparación **léxica TF-IDF** funciona con la instalación base y aparece identificada como tal. Si el modelo semántico falla, la aplicación informa el error; no sustituye silenciosamente el motor.

Estado de validación de esta entrega: el conector OpenAlex recuperó artículos reales. La descarga de los pesos del modelo fue bloqueada por el proxy de este entorno en `us.aws.cdn.hf.co`; por ello aún no se verificó inferencia con esos pesos aquí. El circuito semántico se probó con vectores de prueba inyectados, lo cual no valida la calidad del modelo. Véase `docs/validacion.md`.

## Activar el asistente LLM local (opcional)

Instala **Ollama para Windows** desde https://ollama.com/download/windows y mantenlo abierto. En CMD ejecuta:

```bat
ollama --version
ollama pull qwen2.5:3b
ollama list
```

Después reinicia `iniciar.bat`, abre un candidato con PDF leído y pulsa **Generar propuestas con LLM local**. No se requiere API key ni se envía el PDF a un proveedor en la nube: la aplicación llama a Ollama en `127.0.0.1:11434`. La descarga inicial del modelo requiere Internet y varios gigabytes libres en disco; en un equipo de 8 GB de RAM la inferencia puede tardar minutos. Si Ollama no responde, comprueba que la aplicación esté abierta. Esta integración se probó con respuestas controladas, **no** con inferencia real en este entorno ni con una evaluación científica de calidad. La aplicación inspecciona todas las páginas para seleccionar hasta 12 pasajes: por límites de contexto y memoria, el modelo no recibe las 16 páginas completas en una sola petición. Las citas exactas se validan, pero la selección puede omitir evidencia y las interpretaciones pueden ser erróneas.

## Qué puedes probar

1. Crear la revisión desde el estudio publicado preparado y confirmar su método, o abrir las revisiones manuales anteriores.
2. Editar el protocolo. Cada edición incrementa su versión, invalida el análisis anterior y señala decisiones que necesitan revisión.
3. Importar un PDF base con texto seleccionable (hasta 8 MB y 80 páginas). La extracción recupera texto; la confirmación de pregunta y criterios sigue siendo manual. Sin OCR.
4. Buscar en OpenAlex o DOAJ con consulta, fecha inicial y final, y límite de 25, 50 o 100 registros. Los resultados son de acceso abierto según la fuente. La búsqueda limitada no acredita exhaustividad.
5. Añadir artículos manualmente o importar CSV/JSON. Se omiten duplicados por DOI normalizado o título normalizado.
6. Ejecutar comparación léxica o semántica. Revisar similitud y fragmentos exactos asociados a los criterios. La comparación trabaja con título y resumen, no con el texto completo de cada artículo. Puedes obtener y leer por separado el PDF del candidato desde su expediente.
7. Registrar inclusión/exclusión/pendiente con un motivo. No se producen inclusiones automáticas.
8. Con al menos 3 incluidos y 3 excluidos de la versión actual del protocolo, el siguiente análisis entrena una regresión logística y recomienda etiquetas para pendientes. Las sugerencias no están validadas científicamente.
9. Con al menos 5 incluidos y 5 excluidos, ejecutar una evaluación exploratoria con separación de entrenamiento/prueba, precisión, recall, F1 y matriz de confusión. No sustituye un gold standard independiente.
10. Exportar CSV y generar reportes versionados en JSON y HTML imprimible. El navegador puede imprimir el HTML a PDF. No se reescriben las conclusiones de la revisión original.

Formato CSV/JSON: `title` obligatorio; opcionales `abstract`, `doi`, `year`, `authors`, `url`, `is_oa`. CSV UTF-8, una fila por artículo; JSON debe ser una lista. Máximo 500 registros y 4 MB. No incluyas datos inventados como si fueran publicaciones reales.

## Servicios externos

- OpenAlex: sin clave comparte una cuota diaria con todos los usuarios de tu IP, por lo que puedes recibir HTTP 429 aunque hayas hecho pocas búsquedas. Según su respuesta actual, una clave gratuita da una cuota propia. Puedes obtenerla en https://openalex.org/settings/api. En CMD, antes de `iniciar.bat`, usa `set "OPENALEX_API_KEY=TU_CLAVE"` en **la misma terminal**. No la escribas en archivos del repositorio ni la pegues en el chat. Reinicia el servidor después de configurarla. La aplicación solo muestra si existe una clave, nunca su valor.
- DOAJ: búsqueda de metadatos en revistas de acceso abierto mediante su API pública. Se puede seleccionar en la interfaz cuando OpenAlex esté limitado. La consulta restringe los años antes de paginar y comprueba los meses conocidos en ambos extremos. Si DOAJ informa solo el año, verifica el mes y el día en el artículo antes de incluirlo. Las dos fuentes se consultan por separado y se registra la procedencia.
- Hugging Face: descarga inicial del modelo fijado; después la inferencia es local.
- PDFs candidatos: OpenAlex localiza versiones abiertas por DOI. La descarga final depende del sitio de la revista o repositorio y puede fallar por red, redirecciones o ausencia de un PDF legible; entonces se permite adjuntarlo.
- LLM generativo: integración local opcional con Ollama/qwen2.5:3b, sin cuenta ni clave; requiere instalar y descargar el modelo aparte. Zenodo todavía no está integrado.

## Desarrollo del frontend

Instala Node.js LTS para editar React:

```bat
cd frontend
npm ci
npm run dev
```

Mantén el backend ejecutándose en otra terminal. Vite indica la dirección de desarrollo y dirige `/api` a Python en el puerto 8000. Para generar la versión que sirve Python:

```bat
npm run build
```

Reinicia Python después de compilar. El código está en `frontend/src`; la compilación incluida en `frontend/dist` permite a usuarios sin Node ejecutar el producto.

## Linux y pruebas

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Para IA: instala `requirements-ai.lock` y ejecuta `python -m backend.download_model` con el Python del entorno virtual. Los manifiestos directos están en `requirements.txt`, `requirements-dev.txt` y `requirements-ai.txt`; los archivos `.lock` fijan las versiones resueltas.

## Estructura

- `backend/app/main.py`: API y flujos de trabajo.
- `backend/app/storage.py`: tablas, migraciones y eventos.
- `backend/app/sources.py`: OpenAlex, DOAJ y normalización de duplicados.
- `backend/app/documents.py`: localización de PDF abierto, descarga limitada y extracción por página.
- `backend/app/llm_review.py`: selección de pasajes, LLM local y verificación de citas por página.
- `backend/app/analysis.py`: embeddings, similitud, evidencia y clasificador.
- `backend/app/evaluation.py`: evaluación exploratoria con partición reproducible.
- `frontend/src/`: pantallas React y estilos.
- `tests/`: pruebas con datos sintéticos identificados como fixtures.
- `.agents/skills/frontend-design/`: habilidad de diseño de Anthropic, con licencia Apache 2.0.
- `docs/`: arquitectura, fases y evidencias de validación.

La habilidad de diseño orienta al asistente: no es una biblioteca que se ejecute en el navegador. Se incorporó desde el repositorio oficial de Anthropic, con su licencia y versión documentadas en `docs/design.md`.

## Pendiente antes de considerar terminada la tesis

Autenticación multiusuario, despliegue público seguro, vigilancia programada, PostgreSQL/pgvector, extracción estructurada automática del protocolo, evaluación y calibración independientes de las propuestas LLM, integración de estas en informes, Zenodo Sandbox y evaluación con un gold standard y participantes reales. Esta entrega es un prototipo local avanzado; no una plataforma multiusuario desplegada ni una validación científica final.
