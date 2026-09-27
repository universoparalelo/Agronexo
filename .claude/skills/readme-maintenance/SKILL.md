---
name: readme-maintenance
description: Actualiza README.md de AgroNexo cuando corresponde según las reglas de CLAUDE.md — nuevo servicio en docker-compose, cambio en instalación/requisitos, nuevo comando frecuente, nuevo módulo en app/ o workers/, solución a un problema recurrente, o cambio de variable de entorno. Usar al detectar cualquiera de estos eventos, no en cambios internos triviales.
---

# README maintenance (AgroNexo)

`README.md` es la puerta de entrada para colaboradores. Esta skill se dispara cuando el cambio que se acaba de hacer (o se está por hacer) cae en alguno de los triggers obligatorios de `CLAUDE.md` — no en cada commit.

## Triggers que obligan a actualizar

| Evento detectado | Qué actualizar en README.md |
|---|---|
| Nuevo servicio agregado a `docker-compose.yml` | Tabla de servicios y puertos |
| Cambia el proceso de instalación o los requisitos previos | Sección de instalación |
| Se agrega un comando frecuente nuevo (script, migración, tarea) | Sección "Comandos frecuentes" |
| Se crea un módulo nuevo en `app/` o `workers/` | Árbol de estructura del proyecto |
| Se documenta la solución a un problema recurrente | Sección "Problemas comunes" |
| Cambia alguna variable de entorno requerida | `.env.example` **y** la tabla de variables del README |

Si el cambio no encaja en ninguna fila de esta tabla (refactor, renombrar función, ajustar lógica de negocio interna), **no tocar el README**.

## Procedimiento

1. Confirmar cuál de los triggers de arriba aplica al cambio recién hecho. Si hay dudas, revisar el diff del cambio (`git diff` / `git status`) para ver si tocó `docker-compose.yml`, `.env.example`, `app/`, `workers/`, o algún script nuevo.
2. Leer la sección correspondiente del `README.md` actual antes de editar, para mantener el mismo estilo y formato de tabla/lista que ya existe.
3. Editar solo la sección afectada — no reescribir secciones no relacionadas.
4. Si el trigger es una variable de entorno nueva: actualizar **ambos** archivos en el mismo paso (`.env.example` y la tabla del README), nunca uno sin el otro.
5. Si el trigger es un comando frecuente nuevo: agregarlo en el mismo formato de bloque de código que ya usan los comandos existentes (ver "Comandos frecuentes" en `CLAUDE.md` como referencia de tono/formato).

## Al terminar

Si el evento que disparó esta skill también es una tarea de sprint, recordar que probablemente corresponda también actualizar el archivo de release activo (`docs/release-vX.X.X.md` — ver skill `release-tracking`) y hacer commit/push.
