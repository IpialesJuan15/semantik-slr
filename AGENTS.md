# Semantik SLR

- Aplicación de tesis para revisiones sistemáticas vivas. Interfaz en español, React; API Python/FastAPI. Trabajo local individual hasta implementar autenticación.
- Antes de modificar el diseño, leer `.agents/skills/frontend-design/SKILL.md`, `.agents/skills/interface-design/SKILL.md`, `.agents/skills/ui-ux-pro-max/SKILL.md`, `.interface-design/system.md` y `docs/design.md`. La nueva skill aporta búsquedas locales de patrones; contrastar sus sugerencias con el producto real. La preferencia actual del usuario es fondo claro y rojo cálido, sin morado, verde ni azul oscuro. Mantener estas preferencias aunque una paleta sugerida por la skill indique otros colores.
- Preservar `.local/`: contiene datos del investigador y modelos descargados. No incluir datos personales, credenciales ni pesos de modelos en Git.
- No presentar datos sintéticos, comparación léxica o resultados de pruebas como evidencia científica real. Separar recomendaciones automáticas de decisiones humanas.
- Cuando cambie el frontend, ejecutar `npm --prefix frontend ci` si cambiaron dependencias y `npm --prefix frontend run build`. En este prototipo se versiona `frontend/dist` para ejecutar la aplicación solo con Python en Windows.
- Ejecutar las pruebas pertinentes con `python -m pytest -q`. Conservar versión del protocolo, procedencia, citas exactas e historial al ampliar funcionalidades.
