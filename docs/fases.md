# Avance por fases

| Fase | Entrega actual | Pendiente |
|---|---|---|
| 1. Entorno y aplicación | Windows documentado, scripts de instalación/arranque, React y FastAPI | Verificar scripts BAT en el equipo del usuario |
| 2. Protocolos y revisiones | Crear desde la revisión publicada de Salas-Pilco y Yang; DOI y PDF cotejados; método editable/confirmable; versiones; 31 estudios y categorías originales separados de candidatos nuevos; persistencia migrada | Plantillas generales, extracción metodológica automática con LLM, autenticación |
| 3. Literatura | OpenAlex y conector DOAJ seleccionables; fecha mínima posterior al 30 de junio de 2021 para el caso base; manejo explícito de cuota; límite, importación, deduplicación e historial por fuente | Verificar DOAJ en red con acceso, reproducir las cuatro fuentes originales, consultas multilingües, paginación exhaustiva y evaluar cobertura |
| 4. IA y revisión | Motor semántico integrado con versión/hash fijados, TF-IDF operativo, citas exactas, clasificación supervisada local, decisiones humanas, evaluación exploratoria | Inferencia real en este entorno bloqueada por descarga; calibración y evaluación científica; LLM |
| 5. Actualización | Reportes JSON/HTML versionados con estudio original y nuevos candidatos diferenciados; historial | Extracción estructurada de estudios nuevos, actualización aprobada de tablas, planificador y notificaciones |
| 6. Depósito y validación | Registro local preparado para futura integración | Zenodo Sandbox/DOI, usabilidad con investigadores y gold standard independiente |

El alcance llega funcionalmente a partes de las fases 2, 3, 4 y 5. No se considera ninguna fase científica completa solo por compilar el código. La decisión de inclusión permanece humana.
