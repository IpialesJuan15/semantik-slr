# Versión 0.17 · Soft UI rojo

La interfaz de Semantik adopta una dirección de Soft UI inspirada en la referencia de telemedicina solicitada por el investigador. Se reemplazaron los tonos morados de todos los estilos y del favicon por una paleta de blanco cálido, rojo `#ad3d43`, texto oscuro y bordes suaves. Las tarjetas de revisiones, la lista de artículos, los formularios, las pestañas y el expediente comparten la misma identidad.

La referencia se adaptó al trabajo real: candidatos en lugar de especialistas, PDF y citas en lugar de video, progreso de cribado en lugar de datos de salud. No se añadieron funciones médicas ficticias. Las decisiones y fuentes de la revisión no cambiaron.

El rojo principal sobre blanco alcanza un contraste aproximado de 5.96:1 y los textos secundarios principales superan 4.5:1. La interfaz se comprobó en escritorio y móvil sin desplazamiento horizontal; las animaciones respetan la preferencia de movimiento reducido.

En Windows: detén `iniciar.bat`, ejecuta `git pull --ff-only origin feature/llm-nube-opcional`, inicia de nuevo y recarga con `Ctrl+F5`. `/api/status` debe indicar `0.17.0`. No hay dependencias nuevas.
