# Versión 0.18 · Gemini en lugar de OpenAI

El asistente de PDF ofrece Gemini `gemini-2.5-flash`, Groq y Ollama. Se retiró OpenAI de las solicitudes nuevas y del selector. Los resultados antiguos de OpenAI permanecen guardados con su proveedor original para preservar la trazabilidad.

Gemini usa la API oficial `generateContent` con salida JSON. Recibe título, DOI, criterios y hasta 12 pasajes con sus páginas; el archivo PDF completo no se envía. El servidor valida las citas contra los pasajes y las páginas guardadas antes de mostrar una propuesta. Si Google rechaza la clave, agota la cuota o devuelve una respuesta incompleta, no se guarda la propuesta. La clave no se guarda ni se devuelve a la interfaz.

En CMD de Windows, detén el servidor y ejecuta en la misma ventana `set "SEMANTIK_GEMINI_API_KEY=TU_CLAVE_REAL"` y luego `iniciar.bat`. Comprueba que `/api/status` indique `gemini_key_configured: true` y `version: 0.18.0`. Revisa límites y posibles costos del proyecto en Google AI Studio. La integración se comprobó con respuestas controladas; falta una prueba real con la clave del investigador.
