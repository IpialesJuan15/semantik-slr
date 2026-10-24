# Versión 0.12: lectura del PDF e informes

Se incorporó recuperación semántica local por fragmentos del PDF, preservando páginas y offsets. Usa el modelo MiniLM ya instalado; guarda vectores en SQLite con clave por contenido, hash PDF y revisión del modelo. Se comparan criterios con fragmentos de hasta 420 caracteres y se seleccionan hasta seis, con máximo dos por página. La ventana del tokenizador puede truncar fragmentos con alta densidad de tokens: pendiente evaluar segmentación por tokens y cobertura. Alternativa explícita TF-IDF; nunca se cambia de motor silenciosamente.

El investigador puede localizar pasajes sin usar API y después consultar Groq. La interfaz conserva el criterio seleccionado, muestra enlaces a páginas y espera 60 segundos tras consultas Groq. Las propuestas se comprueban contra el pasaje enviado y la página; las instrucciones exigen cautela con criterios compuestos, fechas y revisión por pares. Esto no garantiza interpretaciones correctas.

Los nuevos informes JSON/HTML conservan evidencia vigente del PDF y propuestas LLM, separadas de decisiones humanas. Las versiones anteriores permanecen inmutables.

Validación: 36 pruebas Python aprobadas y compilación Vite correcta. Caché/recuperación semántica probadas con encoder controlado; falta ejecutar y evaluar el modelo real en Windows y comprobar la nueva interfaz visualmente en navegador. No se utilizó una API key real aquí. No se añadieron dependencias.

Uso: detener servidor, git pull --ff-only en feature/llm-nube-opcional, iniciar.bat y Ctrl+F5. En un candidato con PDF: elegir criterio, localizar pasajes por significado, revisar páginas y pedir explicación a Groq. Si falta el modelo, ejecutar activar-ia.bat o seleccionar explícitamente búsqueda por términos. Generar una nueva versión del informe para incorporar las propuestas vigentes.

Pendientes: evaluación independiente, extracción del protocolo base con LLM, PostgreSQL, autenticación, Zenodo y despliegue. Esta entrega amplía el prototipo; no equivale a completar un porcentaje medido de la tesis.
