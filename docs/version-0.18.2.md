# Versión 0.18.2 · Modelo comprobado en Google AI Studio

El identificador predeterminado de Gemini pasa a `gemini-3.8-flash`, copiado de la lista de modelos que el investigador ve en su Google AI Studio. Se descartaron Gemini 4 Argon y Pro para esta tarea por su mayor costo; Flash Lite es más económico, pero menos capaz. La lista muestra tarifas para 3.8 Flash: no se asume que la clave tenga cuota gratuita.

Se retiró la configuración de razonamiento específica de Gemini 2.5 de la solicitud para no enviar un parámetro potencialmente incompatible con 3.8. La respuesta sigue solicitándose en JSON, con citas comprobadas y decisión humana. Si la API responde 404, la aplicación puede consultar modelos Flash disponibles y registrar el modelo realmente usado; el selector identifica el modelo predeterminado.

Para probar: actualizar la rama en Windows, reiniciar `iniciar.bat` con `SEMANTIK_GEMINI_API_KEY` en esa misma terminal, comprobar `/api/status` versión `0.18.2` y generar una explicación de un PDF leído. Si Gemini devuelve un error, copiar solo el mensaje, nunca la clave.
