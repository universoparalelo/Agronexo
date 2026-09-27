---
name: release-tracking
description: Actualiza el archivo de seguimiento de la release activa (docs/release-vX.X.X.md) de AgroNexo. Usar SIEMPRE al terminar una tarea de sprint, al resolver un error relevante, al tomar una decisión de arquitectura no obvia, o al abrir/cerrar un problema abierto.
---

# Release tracking (AgroNexo)

Cada release de AgroNexo tiene su propio archivo en `docs/release-vX.X.X.md` (una release = un archivo). Esta skill se dispara al cerrar cualquier unidad de trabajo, para dejar registro obligatorio — no es opcional.

## Paso 1 — identificar el archivo activo

1. Abrir `CLAUDE.md` y buscar la línea `**El archivo activo ahora es: ...**` bajo "Seguimiento de release". Ese es el archivo a editar.
2. Si no existe (release recién arrancada), crear `docs/release-vX.X.X.md` copiando la estructura del archivo de la release anterior cerrada más reciente. Nunca modificar el archivo de una release ya cerrada.

## Paso 2 — decidir qué sección actualizar

| Evento | Sección a actualizar |
|---|---|
| Se completó una tarea del sprint | "Tareas completadas" |
| Apareció un error relevante durante la tarea | Dentro de la entrada de la tarea, con el mensaje exacto del error y cómo se resolvió |
| Se tomó una decisión de arquitectura no obvia | "Decisiones de arquitectura" |
| Apareció un problema sin solución | "Problemas abiertos" (agregar) |
| Se resolvió un problema abierto existente | "Problemas abiertos" (borrar la entrada correspondiente) |
| Se cerró la release | Sección "Presentación" + marcar el checklist de cierre |

## Qué NO documentar

- Cambios internos triviales (renombrar variable, ajustar formato).
- Errores de tipeo o sintaxis resueltos en el mismo momento en que aparecieron.
- Decisiones obvias que cualquiera tomaría igual (si no hubo una alternativa real que se descartó, no es una "decisión de arquitectura").

## Formato exacto de entrada de tarea completada

```markdown
#### Nombre de la tarea
**Fecha:** YYYY-MM-DD
**Rama:** `feat/nombre` (commit `abc1234`)

Descripción breve de qué se hizo y por qué.

**Decisiones tomadas:**
- decisión 1
- decisión 2

**Error encontrado — título descriptivo**
[mensaje de error exacto o descripción]
Cómo se resolvió.
```

- La fecha va en formato ISO (`YYYY-MM-DD`).
- El hash de commit se pone recién cuando el commit ya existe (no inventar hashes).
- La sección "Error encontrado" es opcional dentro de la entrada — solo si hubo un error relevante, no cualquier traceback menor.
- Si la tarea no tuvo decisiones no obvias, omitir "Decisiones tomadas" en vez de dejarla vacía.

## Antes de terminar

Después de editar el archivo de release, recordar al usuario (si esta skill se ejecutó como parte de cerrar una tarea) que además debe: (1) hacer commit y push si no lo hizo, y (2) si corresponde, revisar si el evento también dispara una actualización del `README.md` (ver reglas de mantenimiento del README en `CLAUDE.md`).
