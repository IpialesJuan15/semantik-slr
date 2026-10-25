# Skill UI/UX Pro Max

Instalada en [`.agents/skills/ui-ux-pro-max`](../.agents/skills/ui-ux-pro-max/SKILL.md) con `ui-ux-pro-max-cli` 2.15.0 (`uipro init --ai universal`). Fuente: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill, revisión `d14efff8ed1faa4187f004f79926f428c8074ec7`, licencia MIT incluida en la carpeta de la skill. Se conservó solo esta skill; el instalador también generaba otras seis no solicitadas.

Su buscador consulta archivos locales y usa Python 3 sin paquetes adicionales. Ejemplo desde la raíz del proyecto en Windows:

```bat
python .agents\skills\ui-ux-pro-max\scripts\search.py "error summary validation" --domain ux
```

La skill guía decisiones futuras de diseño; instalarla no modifica la interfaz existente. Las preferencias del investigador prevalecen: fondo claro, sin verde ni azul oscuro, y una experiencia sencilla para revisar artículos y registrar decisiones.
