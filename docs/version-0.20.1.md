# 0.20.1 · Lectura completa del texto base

La extracción base envía a Gemini el texto de todas las páginas extraídas, hasta 160 000 caracteres. Sustituye la selección de 24 fragmentos que podía omitir metadatos y continuaciones de criterios. No envía las imágenes ni garantiza lectura de tablas escaneadas; no hay OCR. El mayor contexto puede consumir más tokens o alcanzar la cuota del proveedor.

Se aceptan citas de 8–900 caracteres para permitir DOI y nombres breves. La verificación normaliza espacios, guiones blandos y palabras partidas por un guion al final de línea; no usa coincidencia aproximada ni semántica para aceptar citas.

Al pulsar extraer se reemplazan directamente los campos del formulario con propuestas respaldadas por citas. Los campos sin propuesta conservan lo que el usuario había escrito; deben revisarse. El método solo se guarda al confirmar. Las fechas ausentes no se inventan. No se puede garantizar extracción exhaustiva o interpretación correcta por aumentar el contexto.

Pruebas locales automatizadas con respuestas simuladas. Pendiente validar con el PDF 1-s2.0-S2666557324000521-main.pdf y la cuenta Gemini del investigador.
