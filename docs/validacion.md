# Validación

## Validación adicional de la entrega 0.4

- 16 pruebas automatizadas aprobadas. Las tres nuevas verifican la transformación de registros DOAJ, el filtro anual y DOI, la selección de la fuente, la persistencia de procedencia y el manejo de HTTP 429 sin guardar resultados incompletos.
- React/Vite compiló. En Chromium se comprobó la selección de DOAJ y el botón de búsqueda, sin errores JavaScript. La respuesta real de OpenAlex explicó que las solicitudes sin clave comparten una cuota diaria por IP y ofreció una clave gratuita con cuota propia.
- Se cotejó la ruta y forma de resultados DOAJ con el código fuente público de su API actual (`/api/search/articles/{consulta}`, parámetros `page` y `pageSize`; `bibjson`). El proxy de esta instancia devolvió 403 al intentar `doaj.org`, por lo que la consulta real a DOAJ sigue sin verificarse aquí. Sus pruebas usan respuestas controladas, no una publicación recuperada en vivo.

## Validación adicional de la entrega 0.3

- 13 pruebas automatizadas aprobadas en Python 3.12/Linux. La prueba nueva crea una revisión desde el DOI publicado, comprueba los 31 registros históricos y los recuentos originales, exige PDF y confirmación humana antes de buscar, verifica el corte del 1 de julio de 2021, comprueba que un candidato nuevo no se mezcla con los originales, verifica el reporte y la persistencia tras reiniciar.
- Compilación React/Vite completada. Prueba en Chromium: crear el caso preparado, mostrar los 31 registros, adjuntar un PDF sintético identificado como prueba, confirmar método, añadir un candidato sintético, ejecutar TF-IDF y volver automáticamente a revisar el artículo. Sin errores JavaScript ni desbordamiento horizontal a 390 px.
- Consulta real a OpenAlex desde el flujo de la revisión base: `artificial intelligence higher education Latin America`, desde `2021-07-01` hasta 2026, límite 3; devolvió tres registros, con el resultado marcado como no exhaustivo. Esta consulta se ejecutó en una base de prueba aislada.
- El caso preparado se derivó de la transcripción del artículo aportada por el investigador: Salas-Pilco y Yang (2022), DOI `10.1186/s41239-022-00326-w`, pp. 5–11. Se transcribieron las preguntas, método, 31 citas abreviadas/países y las cinco categorías de la tabla 2. Todavía se requiere cotejo humano con el PDF original. No se han estructurado todos los campos de la tabla 1.
- La inferencia del modelo semántico con pesos reales sigue sin verificarse por el bloqueo de descarga descrito abajo. Tampoco se ejecutaron los BAT en Windows.

## Verificado

- 12 pruebas automatizadas aprobadas con Python 3.12 en Linux, en un entorno virtual nuevo que contiene solo las dependencias base. Cubren persistencia y migración, validación, importación atómica, deduplicación por DOI/título, análisis léxico, offsets/citas exactas, decisiones, versiones de protocolo, reportes inmutables y su hash, CSV seguro, extracción PDF, clasificador, separación de conjuntos y errores del modelo no disponible.
- La prueba del circuito semántico usa un codificador de prueba inyectado. Verifica las operaciones y contratos, no la calidad ni la inferencia de los pesos preentrenados.
- Compilación React con Vite completada.
- Prueba funcional con Chromium/Playwright: creación de revisión, registro de artículo sintético de prueba, análisis léxico, lectura de evidencia, inclusión con motivo, descarga de reporte JSON e historial. Sin errores JavaScript. Se comprobó la vista de 390 px sin desbordamiento horizontal.
- Búsqueda real en OpenAlex mediante la API del sistema: consulta `artificial intelligence higher education`, años 2023–2026, límite 3; se recuperaron y guardaron 3 registros reales. No se presentó esta consulta como búsqueda exhaustiva.
- El resolutor de pip confirmó paquetes binarios disponibles para Windows de 64 bits con Python 3.13, incluidos los requisitos opcionales de IA.
- Modelo fijado a una revisión concreta; tamaños y SHA-256 de pesos y tokenizador comprobados contra la API oficial de Hugging Face. Esto verifica la configuración de la descarga, no que los archivos estén presentes ni que la inferencia funcione.

## Bloqueo observado

La API de Hugging Face responde y entrega metadatos. La descarga de los pesos y el tokenizador redirige a `us.aws.cdn.hf.co`, donde el proxy de este entorno devuelve 403. Se añadieron los dominios requeridos al borrador de red; el acceso efectivo al servidor final sigue pendiente. Los pesos no se han podido cargar en esta instancia y no se declara el análisis semántico real como verificado.

En Windows, `activar-ia.bat` instala las dependencias y descarga los artefactos desde sus fuentes HTTPS oficiales. Se verifican sus hashes antes de cargarlos. Una vez finalizado, seleccionar Similitud semántica, analizar artículos reales y comprobar el resultado en ese equipo. Si vuelve a aparecer 403, habilitar el dominio de descarga en la red utilizada; no desactivar TLS ni cambiar los hashes.

## Todavía no verificado

- Ejecución de los BAT y rendimiento/memoria en el Windows del usuario.
- Inferencia semántica real con el modelo descargado.
- Precisión clínica/científica, recall de recuperación, F1 sobre un gold standard independiente o usabilidad con investigadores.
- Multiusuario, despliegue público, planificador periódico, resumen generativo, Zenodo y DOI.

Las métricas que calcula el programa pertenecen a las etiquetas locales y una partición exploratoria; no son resultados de validación científica de la tesis. Los registros sintéticos de las pruebas no se incluyen como datos iniciales del producto.
