# Versión 0.18.3 · Error temporal 503 de Gemini

Cuando Google responde 503, el asistente espera dos segundos (o el encabezado `Retry-After`, con máximo ocho segundos) y repite la solicitud una sola vez con el mismo modelo. Si Google continúa ocupado, se informa claramente de la indisponibilidad temporal y se sugiere usar Groq mientras tanto. Ninguna propuesta se guarda en caso de error.

El 503 observado por el investigador confirma que la solicitud llegó a Google, pero no permite saber por sí solo si el servicio estaba saturado o si hubo otra indisponibilidad temporal del proveedor. La integración se verificó con respuestas controladas; falta comprobar el nuevo reintento con la cuenta del investigador.
