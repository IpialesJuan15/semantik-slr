# Versión 0.15 · Navegación vertical

La versión 0.14 concentraba demasiadas funciones en bandas horizontales. Esta revisión usa un índice vertical corto en escritorio: «Mis revisiones», «Cargar revisión» y, cuando hay un proyecto abierto, sus secciones. El índice cabe entero en una pantalla de portátil sin desplazamiento propio. En móvil se convierte en una fila superior y las secciones se mantienen como pestañas.

La biblioteca presenta las cifras y el recorrido a la izquierda y los proyectos a la derecha. Dentro de la revisión, el panel de análisis aparece una sola vez cuando es el siguiente paso y «Buscar más estudios» se encuentra junto a la lista de candidatos. La lista y el expediente siguen visibles juntos en escritorio; los saltos internos llevan a resumen, PDF/asistente y decisión.

No se modificaron datos, criterios, decisiones ni funciones del LLM. Para actualizar en Windows, detén `iniciar.bat`, ejecuta `git pull --ff-only origin feature/llm-nube-opcional`, vuelve a iniciarlo y recarga con `Ctrl+F5`. La ruta `/api/status` debe mostrar `0.15.0`.
