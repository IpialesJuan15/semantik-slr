# Versión 0.18.1 · Selección de modelo Gemini

Si el modelo inicial `gemini-2.5-flash` devuelve 404, Semantik consulta con la misma clave el listado de modelos autorizado por Google AI Studio. Entre los modelos Flash que admiten `generateContent`, escoge uno disponible y repite la solicitud una vez. El resultado guarda el nombre exacto del modelo utilizado. No se sustituye automáticamente por un modelo Pro. Si no hay un Flash utilizable, muestra un error sin incluir la respuesta privada del proveedor.

Para fijar un modelo concreto obtenido en Google AI Studio, se puede establecer `SEMANTIK_GEMINI_MODEL` en la misma terminal de CMD antes de `iniciar.bat`. El identificador debe comenzar con `gemini-`; por ejemplo, `set "SEMANTIK_GEMINI_MODEL=gemini-3-flash-preview"` solo si ese nombre aparece para el proyecto. Una selección explícita no activa sustitución automática.

Prueba en Windows: detener el servidor, actualizar con `git pull --ff-only origin feature/llm-nube-opcional`, configurar `SEMANTIK_GEMINI_API_KEY` y ejecutar `iniciar.bat`. `/api/status` indica la versión `0.18.1`. Repetir la explicación con Gemini y verificar la página y el sentido de cada cita. Los resultados antiguos no se modifican.
