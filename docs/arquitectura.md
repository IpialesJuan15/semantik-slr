# Arquitectura y decisiones

React/Vite entrega la interfaz; FastAPI expone una API JSON y sirve la compilación. SQLite mantiene revisiones, artículos, decisiones vigentes, eventos, trabajos de análisis y reportes. Esta entrega es local individual y se inicia en 127.0.0.1.

La migración agrega tablas y columnas sin borrar revisiones anteriores. `.local/reviews.sqlite3` y `.local/models` son privados del equipo y se excluyen de Git. Al cambiar un protocolo se conserva el historial, se invalida el análisis y se marcan decisiones previas como pendientes de revalidación. Las etiquetas de otra versión del protocolo no entrenan el clasificador.

## Modelos

- Semántico: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, versión ONNX cuantizada distribuida por Qdrant. Revisión fijada: `faf4aa4225822f3bc6376869cb1164e8e3feedd0`. Vector de 384 dimensiones. FastEmbed y ONNX Runtime en CPU, dos hilos, lotes de ocho. Los vectores por artículo se obtienen agregando fragmentos de título/resumen, con hasta 80 fragmentos. El tokenizador también impone una ventana máxima por fragmento.
- Referencia léxica: TF-IDF de unigramas y bigramas, hasta 12000 características. No equivale a comprensión semántica ni a traducción entre idiomas.
- Clasificador: regresión logística, balance de clases, semilla 42, etiquetas del investigador. Se entrena dentro de cada revisión a partir de tres ejemplos por clase como mínimo. Ese mínimo permite demostrar el circuito, no asegura calidad. Las recomendaciones no modifican las decisiones humanas.
- Evaluación: partición estratificada 60/40 con semilla 42 a partir de cinco ejemplos por clase. TF-IDF se ajusta exclusivamente al subconjunto de entrenamiento. Se registran IDs de entrenamiento y prueba, métricas y matriz. No se ha establecido un gold standard científico; repetir ajustes sobre el mismo conjunto deja de ser evaluación independiente.

Se eligió ONNX multilingüe para reducir la carga de un equipo Windows con 8 GB de RAM. El modelo e5 y el clasificador NLI mencionados al comienzo de la conversación eran candidatos, no compromisos ya implementados. Esta versión utiliza MiniLM cuantizado y regresión logística; se deben comparar empíricamente antes de elegir la solución final de la tesis.

## Evidencia y trazabilidad

Las fuentes de candidatos son OpenAlex y DOAJ. El intervalo de búsqueda tiene fechas de inicio y fin; el fin nunca pasa de hoy. OpenAlex filtra por fecha completa. DOAJ restringe el año en la consulta antes de paginar y comprueba los meses disponibles de ambos extremos; si faltan día o mes, registra incertidumbre para cotejo humano. La revisión base se excluye de las nuevas importaciones por DOI o título; los registros existentes no se alteran automáticamente. Un HTTP 429 conserva la consulta y se informa con la espera publicada por la fuente cuando existe. OpenAlex sin clave comparte una cuota por IP; `OPENALEX_API_KEY` permite usar una cuota propia. El historial registra la fuente, el intervalo y la procedencia inicial de cada artículo. Estas consultas no reproducen Web of Science, IEEE Xplore, SciELO y CAPES ni son exhaustivas.

La evidencia se extrae de títulos/resúmenes conservando el fragmento y los offsets. La igualdad exacta valida presencia textual; no valida la interpretación ni el cumplimiento del criterio. Se conserva motor, modelo, revisión del modelo, versión del protocolo y hash del texto. No se genera un resumen narrativo ni se afirma analizar el texto completo de cada publicación.

La versión 0.8 agrega `article_documents` sin alterar decisiones ni reportes existentes. Para un candidato con DOI, consulta OpenAlex y prueba hasta cinco URL PDF registradas como abiertas; cada destino/redirección debe ser HTTPS público. Se limita la descarga a 8 MB y la lectura a 80 páginas/160 000 caracteres. También se permite adjuntar PDF autorizado. Se guarda el archivo, SHA-256, procedencia y texto separado por página en SQLite local; la API muestra una vista previa y permite abrir el PDF guardado. Un PDF escaneado sin texto requiere OCR, todavía no implementado. La procedencia de la URL no verifica por sí sola la identidad del documento: el investigador debe cotejar título y DOI. El motor semántico y los reportes no consumen aún este texto; se deja preparado para una futura generación de justificaciones con citas por página.

El trabajo de análisis se ejecuta en un único worker para controlar memoria. Su estado persiste y se informa una interrupción tras reiniciar. No existe todavía un planificador de búsqueda periódica. Los reportes guardan una instantánea inmutable del estado y su SHA-256. El CSV se protege frente a fórmulas al abrirlo en una hoja de cálculo.
