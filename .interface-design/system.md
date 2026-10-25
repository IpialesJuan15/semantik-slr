# Sistema de interfaz · Semantik SLR

Skill aplicada: Interface Design de Damola Akinleye (`.agents/skills/interface-design/SKILL.md`), revisión `2f9be3206855bcb2d1d0af262c8bae25cba6658d`, licencia MIT. Se complementa con la dirección visual previa del proyecto.

## Intención

Investigador que acaba de recuperar artículos y necesita contrastar cada candidato con una revisión publicada. Debe ver el siguiente paso sin adivinar qué pestaña abrir, leer la evidencia al lado de la lista y dejar una decisión motivada. La pantalla debe sentirse como una mesa de lectura académica: calmada, rigurosa y clara.

Dominio: protocolo, publicación base, fuente, candidatos, fragmentos, decisiones, historial e informe. Mundo físico: papel blanco, márgenes de anotación violeta, tinta gris cálida, separadores discretos y señal ámbar para tareas pendientes. La firma de la interfaz es la **lista de lectura junto al expediente del artículo**, precedida por una guía de siguiente paso calculada con el estado real de la revisión.

## Tokens y composición

- Fondo `#f7f7fa`, papel `#ffffff`, tinta `#34313d`, anotación `#7251a2`, texto secundario `#746a7e`, línea `#e4e2eb`, control inset `#faf8fc`. Sin verde, azul oscuro ni superficies oscuras.
- Estrategia de profundidad: superficies claras y bordes suaves; el foco violeta se reserva a acciones y selección. Sin sombras decorativas ni degradados.
- Escala de espacio basada en 4 px. Controles de al menos 40 px, con 44 px como objetivo en móvil. Tarjeta guía: 25–28 px de relleno; columna de lista: 17 px; filas: 14 px verticales.
- Tipografía Aptos/Segoe UI para la herramienta y Georgia para resúmenes/citas documentales. Jerarquía por peso y contraste; títulos de guía 22 px, títulos de sección 18 px, controles y cuerpo 13 px, metadatos 11 px.
- Escritorio: lista de candidatos 37 %, expediente 63 %, con 20 px de separación. Móvil: columnas apiladas, lista con altura limitada para llegar al expediente sin desplazamiento interminable.

## Patrones

- **Siguiente paso**: una indicación y una acción principal según confirmación del estudio base, existencia de candidatos, análisis y decisiones. La barra muestra revisados/total; nunca es una métrica decorativa.
- **Búsqueda**: visible al iniciar; cuando ya hay candidatos se reduce a “Buscar más estudios”. La fuente preferida se recuerda por sesión. Se conserva el aviso de alcance metodológico.
- **Fechas**: dos fechas completas nombradas “Publicados desde” y “Hasta (incluido)”. El final predeterminado es hoy; el inicio de una revisión publicada es el día siguiente al último incluido. La lista guardada tiene un filtro separado por años para evitar confundir búsqueda nueva con artículos persistidos.
- **Análisis**: se ejecuta en la misma vista de artículos. Tras completarse, las opciones se recogen y se privilegia la lectura. La evaluación exploratoria queda en un desplegable secundario.
- **Lectura y decisión**: lista y expediente visibles juntos en escritorio; en móvil la elección lleva al expediente. Guardar una decisión avanza al siguiente pendiente. Las recomendaciones automáticas permanecen separadas de la decisión humana.

## Ajustes de la versión 0.7

- **Búsqueda visible**: la última consulta muestra fuente, intervalo, consulta y recuperados frente al total declarado por la fuente. El aviso de resultados por recorrer es ámbar; nunca se presenta como cobertura exhaustiva.
- **Filtros reconocibles**: cada filtro de la lista tiene una etiqueta visible. Los años proceden de la última búsqueda registrada; cambiar la siguiente consulta no altera la vista guardada. La lista indica con palabras que filtrar no borra datos.
- **Decisiones antiguas**: el aviso del protocolo lleva directamente a los registros afectados y abre el siguiente después de guardar. El investigador puede distinguir proyectos con el mismo título por número y fecha.
- **Expediente**: título, procedencia, resumen y formulario de decisión tienen una jerarquía clara. Los fragmentos automáticos son un desplegable secundario, etiquetado como parecido textual que requiere cotejo; ningún puntaje se presenta como probabilidad o prueba.
- **Informes**: antes de crear un reporte con pendientes, un aviso explica que será un borrador y ofrece volver al trabajo de revisión.

## Ajuste de la versión 0.8

- **Documento del candidato**: sección blanca con borde suave entre resumen y evidencia. Muestra estado de lectura, páginas, procedencia y advertencia de cotejo; los fragmentos por página permanecen plegados. Buscar PDF abierto y adjuntar PDF comparten la misma sección. «PDF leído» no implica que el análisis ni el LLM hayan examinado el texto.

## Ajuste de la versión 0.9

- **Asistente local**: dentro del documento, bajo la vista previa y antes de las pistas semánticas. Presenta una propuesta por criterio con cita/página o incertidumbre explícita. El bloque se nombra «Asistente de lectura del PDF» para distinguirlo de la decisión humana y de los puntajes de título/resumen.

## Ajuste de la versión 0.10

- **Proveedor del LLM**: un selector etiquetado dentro del asistente ofrece nube o equipo. La explicación inmediatamente debajo declara qué pasajes se envían, el posible costo y el requisito de clave. La propuesta conserva el nombre del proveedor, sin mezclarla con la decisión humana.

## Ajuste de la versión 0.11

- **Groq por criterio**: al elegir Groq aparece un segundo selector de criterio. La explicación del plan gratuito queda junto a la acción. El expediente muestra progreso de criterios consultados y distingue los todavía no analizados de respuestas inciertas.

Rechazos deliberados: tablero de tarjetas métricas repetidas, una pestaña separada para cada acción del mismo artículo, puntuación tratada como probabilidad de inclusión. Mantener siempre los estados vacío, error, ocupación, foco y móvil.

## Ajuste de la versión 0.14

- La navegación usa una barra superior de 64 px en escritorio y una fila compacta en móvil. La mesa de lectura aprovecha el ancho antes ocupado por la barra lateral.
- Las pestañas de sección y la navegación interna del expediente permanecen a la vista al desplazarse. Los saltos llevan directamente a resumen, PDF/asistente o decisión.
- La guía contextual, el recibo de búsqueda y la configuración de análisis ya terminado reducen su altura. Los filtros de año y estado se muestran bajo demanda; la búsqueda por título permanece visible.
- El resumen conserva el texto completo y permite expandirse. Ningún bloque automático se interpreta como decisión del investigador.

## Ajuste de la versión 0.15

- El índice de escritorio se organiza verticalmente: navegación general arriba, secciones de la revisión debajo. Sus siete acciones como máximo caben sin desplazamiento.
- La biblioteca muestra cifras y recorrido en una columna secundaria, junto a los proyectos. El contenido deja de formar bandas del ancho total.
- La pantalla de candidatos evita repetir una indicación de análisis encima de los propios controles de análisis. La acción de nueva búsqueda vive en la cabecera de artículos.
- En pantallas estrechas el índice se transforma en una fila superior y las secciones se muestran en pestañas desplazables.

## Ajuste de la versión 0.16

- UI/UX Pro Max se consultó para portafolios creativos, brutalismo, patrones de contenido y movimiento accesible. La adaptación conserva el dominio de la revisión sistemática.
- Una sola pieza expresiva domina la portada: marco, título grande y número real de proyecto en cada vista previa. El expediente mantiene jerarquía documental y citas legibles.
- La portada y el artículo seleccionado usan animaciones cortas; la preferencia de movimiento reducido las desactiva. No se usan parallax ni desplazamiento forzado.
