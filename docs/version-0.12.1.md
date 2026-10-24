# Versión 0.12.1: selección prudente de evidencia

La prueba manual con Bashayer mostró que los embeddings priorizaban contexto general y referencias de otros estudios, incluida una conferencia latinoamericana en la bibliografía. Esos pasajes no demuestran el lugar del estudio principal.

La recuperación ahora corta en el encabezado de referencias/bibliografía, prioriza fragmentos que hablan explícitamente del estudio, muestra como máximo tres pasajes y, para criterios geográficos, no ofrece un pasaje sin señales del estudio principal. Si no hay pasajes, la API evita consultar Groq. La interfaz aclara que debe comprobarse el PDF y muestra un estado de evidencia insuficiente.

La puntuación sigue siendo una ayuda de selección y estas reglas pueden omitir evidencia válida o dejar entrar citas incrustadas. No se afirma precisión científica ni cobertura exhaustiva. Validación: 37 pruebas Python aprobadas, incluida una reproducción controlada del fallo con referencias, y compilación React/Vite. Pendiente probar el PDF real de Bashayer y otros formatos en Windows.

Ajuste 0.12.2: el flujo principal queda en una sola acción («Buscar evidencia y explicar con Groq»). La vista previa y el cambio de motor pasan a un desplegable opcional. El servidor sigue bloqueando la llamada al LLM cuando no hay pasajes del estudio principal para ese criterio.

Ajuste 0.12.3: a partir del resultado real del investigador con Bashayer se excluye además la sección de contribuciones de autores y otros anexos finales. Para criterios geográficos, un pasaje debe relacionarse con el estudio principal y contener una señal explícita de lugar. Estas reglas pueden omitir una formulación válida no reconocida; la falta de pasajes no significa exclusión automática.
