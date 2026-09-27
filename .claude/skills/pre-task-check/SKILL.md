---
name: pre-task-check
description: Verifica si hay cambios remotos en origin/main que el local de AgroNexo no tiene, ANTES de empezar cualquier tarea nueva (regla obligatoria de CLAUDE.md). Si hay commits nuevos, no se limita a listarlos — resume en lenguaje claro qué se hizo funcionalmente y por qué, y recién después pregunta si se quiere traer los cambios.
---

# Pre-task check (AgroNexo)

`CLAUDE.md` exige correr esto antes de iniciar cualquier tarea. El punto no es solo detectar que hay commits nuevos, sino **entender y contar** qué cambió, para que el usuario decida con contexto real si conviene traerlos antes de seguir.

## Paso 1 — traer y comparar

```bash
git fetch origin
git log --oneline origin/main ^main
```

Si no hay salida: el local está al día con `origin/main`. Decirlo brevemente y seguir con la tarea sin más trámite — no hace falta el resto de los pasos.

Si hay salida: hay commits en el remoto que el local no tiene. Continuar al paso 2. Nunca asumir que el local está al día solo porque "parece reciente".

## Paso 2 — entender qué se hizo (no solo listar)

Para cada commit (o el lote completo si son varios relacionados), mirar más que el subject de una línea:

```bash
git log origin/main ^main --format='%h %s%n%b' 
git diff main origin/main --stat
```

Usar el `--stat` para ver qué áreas del proyecto tocó (frontend, un módulo de `app/`, `workers/`, migraciones, CI, docs) y el body de los commits para entender el motivo, no solo el qué.

## Paso 3 — armar el resumen (esto es lo importante)

No pegar la lista cruda de `git log --oneline`. Sintetizar en 3-6 líneas, en términos funcionales, algo como:

> "Desde que arrancaste, en `main` se mergeó el fix del refresco de zonas en el dashboard (bf7afa0) y una mejora de la vista del EXG/GNDVI con normalización de valores para que el motor de reglas pueda usarlos (22d4ee9). También se unificó la navegación con una barra lateral en todas las pantallas del panel (a8cf16e). Ningún cambio toca las áreas en las que vas a trabajar / [o sí toca X, ver abajo]."

Si algún commit remoto toca archivos que la tarea planeada también va a tocar (mismos módulos, mismos componentes), marcarlo explícitamente como riesgo de conflicto.

## Paso 4 — preguntar, no decidir solo

Preguntar explícitamente si se quiere traer los cambios ahora (`git pull`) antes de seguir, especialmente si el paso 3 detectó superposición con lo que se va a tocar. Si el usuario dice que no, seguir con la tarea sobre el estado local actual sin insistir.

## Qué NO hacer

- No hacer `git pull` ni ningún merge por cuenta propia sin que el usuario lo pida — esto es solo diagnóstico e informe.
- No limitarse a repetir la salida de `git log --oneline` como si fuera el resumen — eso es el insumo, no el resultado.
