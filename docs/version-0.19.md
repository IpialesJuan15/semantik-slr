# Versión 0.19 · Gemini por criterio y modelo elegible

Gemini analiza un criterio seleccionado por solicitud en lugar de enviar todos los criterios de la revisión juntos. Esto reduce los pasajes enviados, el tamaño de respuesta y el trabajo por solicitud; no garantiza resolver un error 503 del proveedor. Las propuestas se acumulan por artículo, PDF, protocolo y modelo. Si se cambia de modelo, los resultados de 3.8 Flash y 3.5 Flash Lite se conservan separados. La decisión humana no cambia.

La interfaz permite elegir `gemini-3.8-flash` (mayor capacidad) o `gemini-3.5-flash-lite` (menor costo), identificadores copiados de la lista que el investigador ve en Google AI Studio. Ninguno se presenta como gratuito: la cuenta determina límites y tarifas. Ante 503 persistente en 3.8 Flash, se puede probar Lite directamente en la página, con un solo criterio. Si Lite también devuelve 503, el problema no queda resuelto por esta selección; conviene continuar con Groq y revisar el estado/acceso de la API de Google.

Actualización Windows: detener el servidor, `git pull --ff-only origin feature/llm-nube-opcional`, iniciar de nuevo con la clave Gemini en la misma terminal y recargar con Ctrl+F5. `/api/status` debe indicar `0.19.0`. Las pruebas locales usan respuestas controladas; hace falta la prueba real con la cuenta del investigador.
