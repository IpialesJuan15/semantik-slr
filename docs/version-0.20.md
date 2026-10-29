# Versión 0.20 · Método base y evidencia dentro de Semantik

## Revisión base

1. En **Cargar revisión publicada**, adjunta el PDF de una revisión sistemática. El título y DOI son opcionales al crear el borrador. No se insertan los criterios del caso preparado en otros documentos.
2. Pulsa **Extraer preguntas y criterios con Gemini**. Se envían hasta 24 pasajes seleccionados del método, no el PDF binario. Requiere SEMANTIK_GEMINI_API_KEY en la terminal del servidor; la API tiene límites y posibles costos.
3. Inspecciona los datos propuestos y sus citas. Usa **Completar campos vacíos** o copia cada campo con su botón. Puedes editarlo antes de guardar. Los datos sin citas comprobables quedan vacíos.
4. Confirma preguntas, criterios y fecha final del corpus original. Marca únicamente los criterios temporales históricos que deban sustituirse para actualizar. La fecha de publicación de la revisión no equivale al último día buscado.
5. Pulsa **Confirmar y guardar el método**. Los cambios relevantes versionan el protocolo; las decisiones anteriores requieren revisión. La propuesta conserva modelo, hash del documento y citas en la instantánea del método.

Los PDF base cargados en versiones antiguas deben adjuntarse de nuevo una vez para recuperar las páginas. La extracción no reconstruye automáticamente las tablas de todos los estudios originales. Si el documento no declara una fecha completa, debes establecerla y justificarla antes de buscar actualizaciones.

## Candidatos

La búsqueda del PDF conserva grupos de oraciones con mayor contexto y prioriza pasajes del lugar, método y herramienta utilizada. Gemini y Ollama pueden aportar hasta tres citas por criterio; Groq conserva respuestas breves para su límite de salida. Las citas se verifican en la página y en los pasajes enviados; el contexto mostrado procede del documento, no del modelo.

El asistente muestra primero la explicación, las citas y lo que falta aclarar. **Leer página aquí** abre su texto dentro del expediente sin llamar al proveedor. Los controles avanzados y pasajes recuperados quedan plegados. Gemini Flash Lite es la selección inicial; siguen disponibles Flash, Groq y Ollama. Las propuestas antiguas se identifican y se pueden regenerar, sin cambiar automáticamente las decisiones.

Los reportes nuevos conservan las citas múltiples y sus límites. Las versiones anteriores no cambian. Localizar una cita no verifica su interpretación científica ni garantiza que se hayan recuperado todos los pasajes relevantes.

## Actualizar en Windows

Detén el servidor con Ctrl+C. En la carpeta del repositorio:

```bat
git pull --ff-only origin feature/llm-nube-opcional
iniciar.bat
```

Configura la clave Gemini en esa misma terminal antes de iniciar si no está disponible. Nunca la subas al repositorio ni la compartas por chat. Recarga el navegador con Ctrl+F5 y verifica versión 0.20.0. Si Git informa cambios locales, consérvalos antes de actualizar.

## Alcance y validación

PDF con texto seleccionable: hasta 8 MB, 80 páginas y 160 000 caracteres. Sin OCR. Pruebas automatizadas con respuestas de proveedor simuladas; la respuesta real de Gemini depende de la cuenta del investigador. Las pruebas no equivalen a una evaluación científica de precisión.

Python/FastAPI, React y SQLite siguen siendo la arquitectura actual. Oracle, APEX, SciBERT, PICO/SPIDER, vigilancia periódica, UTN Móvil y Zenodo no se añaden en esta entrega. La separación del procesamiento en Python permite preparar su integración posterior, pero no constituye ya una migración.
