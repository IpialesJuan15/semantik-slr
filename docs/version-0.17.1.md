# Versión 0.17.1 · Explicaciones del PDF

La recuperación de pasajes para criterios empíricos ahora prioriza diseño, participantes, recolección y análisis de datos del estudio principal. Descarta frases que solo indican cuándo ocurrió el estudio. Es una heurística; la persona investigadora debe comprobar el método en el PDF.

Una propuesta que afirma o niega carácter empírico necesita una cita metodológica pertinente. Si Groq cita únicamente el periodo del estudio, la propuesta pasa a «cita insuficiente» y deja de afirmar que el criterio se cumple. Las propuestas anteriores se conservan, pero la interfaz avisa que deben consultarse de nuevo; los informes ya generados permanecen históricos.

Los fragmentos de título y resumen sin texto ahora muestran una explicación en vez de un bloque de cita vacío. No cambian las decisiones humanas ni las claves API. Para probar en Windows: detener el servidor, `git pull --ff-only origin feature/llm-nube-opcional`, iniciar de nuevo y recargar con `Ctrl+F5`. `/api/status` debe indicar `0.17.1`. En el artículo de Costa Rica, consultar de nuevo «Investigación primaria empírica» y revisar la cita en el PDF.
