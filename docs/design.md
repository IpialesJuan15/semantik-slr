# Dirección visual

Se aplica Frontend Design de Anthropic, incorporada sin cambios en `.agents/skills/frontend-design`, desde https://github.com/anthropics/skills (commit dbd4588f9e1033efb41dad4bef2f7947c8993d44). Licencia Apache 2.0 incluida.

Usuarios: investigadores que actualizan revisiones sistemáticas. Trabajo principal: inspeccionar evidencia, conocer su procedencia y registrar decisiones justificadas.

Paleta: blanco #ffffff, superficie #f7f7fa, borde #e4e2eb, texto #34313d, acento violeta #7251a2, aviso ámbar #956317. Fondos claros en toda la interfaz; sin verde, azul oscuro ni paneles oscuros. Tipografía Aptos/Segoe UI para controles y Georgia solo para citas documentales. Contenido alineado a la izquierda.

Estructura: navegación lateral blanca; lista de proyectos; al abrir uno, pestañas para estudio base, trabajo con candidatos, informes, historial y protocolo. Buscar, analizar y decidir comparten una vista. La tabla de evidencia y sus fragmentos citados constituyen el foco. No se muestran números simulados ni métricas decorativas. Los colores representan estados, con texto además del color.

Revisión previa: se descarta el panel oscuro anterior y el tablero de tarjetas repetidas. Se usan filas de artículos, citas legibles, controles con nombres explícitos y un espacio de trabajo común para las decisiones. Formularios con etiquetas, foco visible, estados vacíos accionables, errores conservando datos y adaptación a móvil.

Revisión 0.3: el primer objeto visible en una revisión publicada es la ficha del artículo original con DOI y estado de confirmación. La secuencia numerada responde al trabajo real: estudio base, búsqueda/revisión, análisis y reporte. Los 31 estudios originales aparecen en una tabla documental separada del listado de candidatos. Se conservaron las superficies claras y violeta moderado; el énfasis visual se reserva a la procedencia del estudio base, sin agregar tarjetas decorativas. La prueba móvil de 390 px no mostró desbordamiento horizontal.

Revisión de usabilidad: se añadió la skill [Interface Design](../.agents/skills/interface-design/SKILL.md) de Damola Akinleye, instalada en el proyecto desde su repositorio oficial (commit `2f9be3206855bcb2d1d0af262c8bae25cba6658d`, licencia MIT). Sus decisiones específicas se guardan en [system.md](../.interface-design/system.md). Buscar, analizar, leer y decidir comparten un mismo espacio de trabajo. La guía superior señala la siguiente acción y la lista de lectura se coloca junto al artículo abierto. La búsqueda y los controles de análisis se reducen después de utilizarlos para priorizar el contenido científico.
