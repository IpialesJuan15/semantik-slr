# Validación

## Validación adicional de la entrega 0.11

- El investigador probó manualmente `qwen/qwen3.8-27b` en Groq Playground: con `max_completion_tokens=300` devolvió JSON que señalaba correctamente que el estudio Bashayer en Arabia Saudita no cumple el criterio de América Latina y citaba el pasaje aportado de la página 8. El primer intento con una reserva de 1 509 tokens recibió HTTP 429 porque su organización tiene límite de 1 000 tokens de salida por minuto. Esta prueba de un pasaje no valida el comportamiento con selección automática del PDF.
- 31 pruebas Python aprobadas y compilación React/Vite correcta. Las pruebas nuevas verifican el identificador exacto de Groq, el tope de 300 tokens, la selección de un criterio, la verificación de cita y la acumulación de propuestas sin cambiar la decisión humana. La API de Groq se simuló; no se usó ninguna clave real. La versión 0.11.1 añade pruebas para el objeto JSON directo, el bloque Markdown y el corte de respuesta por límite de tokens, después de que el investigador obtuvo un error de formato en Windows. La respuesta real no se ha inspeccionado: estas pruebas cubren causas posibles, no prueban cuál ocurrió.
- Chromium con base sintética aislada a 1365 y 390 px: selector de Groq, criterio, progreso y estado «Aún no analizado», aviso de clave ausente; sin errores JavaScript ni desbordamiento. Falta probar la llamada real a Groq desde Windows y evaluar resultados en varios artículos.

## Validación adicional de la entrega 0.10.1

- Tras la primera prueba real en Windows, OpenAI respondió HTTP 429. El aviso original no distinguía cuota insuficiente de límite temporal; no se guardó ninguna propuesta. La causa exacta de la cuenta del investigador aún debe comprobarse en Facturación/Uso/Límites.
- 25 pruebas Python aprobadas y compilación React/Vite correcta. Se añadieron respuestas 429 sintéticas para `insufficient_quota`, `rate_limit_exceeded` con `Retry-After` y error sin código. El aviso distingue los dos primeros y no devuelve el mensaje original del proveedor ni la clave. No se ha efectuado otra solicitud real desde este entorno.

## Validación adicional de la entrega 0.10

- 22 pruebas Python aprobadas y compilación React/Vite correcta. Una prueba nueva simula la API en nube: verifica que solo se envían título, DOI, criterios y pasajes seleccionados, que se registran proveedor y tokens, y que una cita inventada no se presenta como evidencia. Otra verifica la elección de proveedor en la API. Ninguna prueba usa una clave real ni valida la calidad científica del modelo.
- Chromium con base sintética aislada, a 1365 y 390 px: selector nube/local, aviso sobre datos enviados y costos, y error claro al no configurar la clave. Sin errores JavaScript ni desbordamiento horizontal. Una propuesta anterior permanece visible con su proveedor al fallar una nueva solicitud.
- Pendiente: prueba real con clave de API del investigador, revisión humana de las citas y comparativa controlada frente a Ollama. El usuario no debe compartir la clave por chat ni guardarla en Git.

## Validación adicional de la entrega 0.9

- El investigador comprobó en Windows la descarga automática del artículo de Bashayer (DOI `10.3389/fpsyg.2023.1129070`): 16 páginas y 92 707 caracteres extraídos. El PDF está disponible en la fuente de Frontiers y la app guardó su procedencia. El texto extraído presentó glifos numéricos como `/one.tnum`; la nueva versión repara estos patrones en la vista y antes de seleccionar pasajes. La coincidencia de título/DOI y las interpretaciones siguen requiriendo cotejo humano.
- 21 pruebas Python aprobadas y compilación React/Vite correcta. Las pruebas nuevas verifican normalización de glifos, validación de citas por página, rechazo de cita inventada, independencia de la decisión humana e invalidación de propuestas tras cambiar el protocolo. Son respuestas LLM sintéticas, no miden calidad del modelo.
- Chromium en base aislada con una propuesta sintética identificada como tal: panel LLM a 1365 y 390 px, sin errores JavaScript ni desbordamiento. Si Ollama no está instalado, el botón muestra una instrucción concreta y conserva la propuesta previa. Inferencia real de `qwen2.5:3b` en Windows aún pendiente.

## Validación adicional de la entrega 0.8

- 18 pruebas Python aprobadas y compilación React/Vite correcta. Las pruebas nuevas verifican que el PDF de un candidato se guarda con procedencia, hash y texto por página; que un enlace abierto fallido permite probar otra ubicación; que un archivo inválido no sustituye el anterior; que la decisión humana no cambia; y que se rechazan direcciones locales/privadas.
- Chromium con base sintética aislada: expediente con PDF leído a 1365 y 390 px, enlace al archivo y vista previa por página, sin errores JavaScript ni desbordamiento horizontal.
- OpenAlex devolvió ubicaciones PDF reales para DOI `10.3389/fpsyg.2023.1129070`, pero este entorno no pudo descargar ni la ubicación de Frontiers ni la alternativa de PMC por su proxy/red. La descarga de un PDF real debe probarse en el equipo Windows del investigador; la carga manual y lectura se comprobaron con un PDF sintético. No se ha integrado LLM ni OCR.

## Validación adicional de la entrega 0.7

- Compilación React/Vite y 16 pruebas Python aprobadas. Sin nuevas dependencias ni cambios en los datos del investigador.
- En Chromium, con base sintética aislada, se verificaron escritorio de 1365 px y móvil de 390 px: recibo de búsqueda parcial, acceso a decisión antigua y retorno al flujo pendiente, filtro de años 2021–2024 que oculta el registro de 2026, apertura de expediente y fragmentos, aviso de borrador del informe y revisión publicada con sus 31 estudios originales. No hubo errores JavaScript ni desbordamiento horizontal.
- La prueba detectó y corrigió una confusión previa: al recargar una revisión, los años de la lista ahora siguen la última búsqueda registrada, aunque el valor predeterminado del formulario sea la fecha de hoy.

## Validación adicional de la entrega 0.6.1

- El investigador probó en Windows la búsqueda DOAJ acotada al 2021-07-01–2024-12-31: recuperó 25 candidatos de 994 resultados declarados por la fuente. La consulta funciona allí, pero solo recorrió la primera página y no representa una búsqueda exhaustiva.
- El investigador ejecutó el modelo semántico local sobre 41 registros reales: el trabajo terminó y la interfaz mostró el modelo y fragmentos. Los puntajes incluyeron falsos indicios de cumplimiento de criterios, por lo que no se interpretan como decisiones ni validación científica.
- Una base de prueba aislada con un registro antiguo de la propia revisión base verifica que la API lo identifica, lo omite del recuento de candidatos, análisis, CSV y tabla principal del nuevo reporte, y lo conserva aparte en el JSON. Los reportes con pendientes se etiquetan como borrador. Los reportes anteriores permanecen inmutables.

## Validación adicional de la entrega 0.6

- Las 16 pruebas verifican ahora que el intervalo completo llega a OpenAlex, que DOAJ restringe el año antes de paginar y comprueba meses de ambos extremos, y que la propia revisión base se omite aunque la fuente la devuelva. Se rechazan fechas finales futuras.
- El investigador mostró que su base de Windows contiene la revisión publicada de 2022 marcada como candidata incluida. La nueva interfaz avisa para que revise esa decisión; no modifica ni elimina datos previos automáticamente.
- DOAJ con la nueva consulta de intervalo no pudo probarse en vivo desde este entorno por el proxy 403 descrito abajo; posteriormente el investigador la probó con éxito en Windows. La forma de la consulta se cotejó con el código de la API DOAJ, y la transformación de resultados se probó con respuestas controladas.
- En Chromium, con una base sintética aislada que imitaba el registro previo, se comprobó el aviso del estudio base, el rango predeterminado 2021-07-01 a hoy, el filtro de años guardados y la explicación de fechas en Estudio base. Sin errores JavaScript ni desbordamiento horizontal a 390 px.

## Validación adicional de la entrega 0.5

- La skill Interface Design se incorporó al proyecto desde su repositorio oficial, commit y licencia anotados en `docs/design.md`. La interfaz usa una guía contextual, análisis en la misma vista y expediente junto a la lista de lectura.
- En Chromium se probó el flujo con datos sintéticos aislados: analizar con TF-IDF, abrir el primer pendiente, guardar una decisión y avanzar al siguiente. No hubo errores JavaScript ni desbordamiento horizontal a 390 px. Estos datos no se incorporaron al producto.
- El investigador informó que la consulta DOAJ en su equipo devuelve artículos candidatos. La prueba automatizada del conector y la limitación de acceso de este entorno se documentan abajo.

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

- Medición controlada de rendimiento/memoria y repetición independiente de la inferencia semántica en Windows; el usuario informó que `iniciar.bat` y el análisis semántico funcionaron.
- Precisión clínica/científica, recall de recuperación, F1 sobre un gold standard independiente o usabilidad con investigadores.
- Multiusuario, despliegue público, planificador periódico, resumen generativo, Zenodo y DOI.

Las métricas que calcula el programa pertenecen a las etiquetas locales y una partición exploratoria; no son resultados de validación científica de la tesis. Los registros sintéticos de las pruebas no se incluyen como datos iniciales del producto.
