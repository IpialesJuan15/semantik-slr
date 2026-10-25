# Versión 0.14 · Mesa de lectura compacta

La navegación lateral se reemplazó por una barra superior. En la revisión, las pestañas permanecen visibles, la guía de siguiente paso y la última búsqueda ocupan menos altura y la lista de candidatos tiene búsqueda permanente con filtros secundarios plegables. El expediente ofrece accesos directos a resumen, PDF/asistente y decisión; los resúmenes largos se pueden expandir. La aplicación mantiene las mismas funciones, datos y decisiones humanas.

Para actualizar en Windows, cierra la aplicación, ejecuta `git pull --ff-only origin feature/llm-nube-opcional` dentro de la carpeta del proyecto y vuelve a ejecutar `iniciar.bat`. Después abre `http://127.0.0.1:8000` y recarga con `Ctrl+F5` si el navegador conserva la versión anterior. No hace falta reconstruir React ni instalar dependencias nuevas porque `frontend/dist` está versionado.

Comprobación sugerida: abre una revisión con candidatos, entra en **Buscar y decidir**, abre uno y usa **Tu decisión** para saltar al formulario; usa **PDF y asistente** para volver a la evidencia. En móvil, la lista aparece encima del expediente.
