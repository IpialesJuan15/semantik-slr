# Semantik SLR

- Aplicación de tesis para revisiones sistemáticas vivas. Interfaz en español, React; API Python/FastAPI. Trabajo local individual hasta implementar autenticación.
- Antes de modificar el diseño, leer `.agents/skills/frontend-design/SKILL.md` y `docs/design.md`. El usuario pidió fondos claros, sin verde ni azul oscuro. Mantener estas preferencias.
- Preservar `.local/`: contiene datos del investigador y modelos descargados. No incluir datos personales, credenciales ni pesos de modelos en Git.
- No presentar datos sintéticos, comparación léxica o resultados de pruebas como evidencia científica real. Separar recomendaciones automáticas de decisiones humanas.
- Cuando cambie el frontend, ejecutar `npm --prefix frontend ci` si cambiaron dependencias y `npm --prefix frontend run build`. En este prototipo se versiona `frontend/dist` para ejecutar la aplicación solo con Python en Windows.
- Ejecutar las pruebas pertinentes con `python -m pytest -q`. Conservar versión del protocolo, procedencia, citas exactas e historial al ampliar funcionalidades.
