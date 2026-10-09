#!/usr/bin/env bash
# Backup programado del bucket de MinIO (HU-R4-06). Los GeoTIFF originales no
# se pueden recalcular, así que esto no es opcional. Pensado para correr vía
# cron en el host del servidor de producción.
#
# Usa `mc mirror` DENTRO del propio contenedor minio (la imagen
# cgr.dev/chainguard/minio trae el cliente `mc`) contra un volumen separado
# del de datos, montado en docker-compose.prod.yml como minio_backups.
#
# Uso: ./scripts/backup_minio.sh
# Cron sugerido (diario a las 3:30am, conserva los últimos 14 días):
#   30 3 * * * cd /ruta/al/repo && ./scripts/backup_minio.sh >> backups/minio/backup.log 2>&1

set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
RETENCION_DIAS=14

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: no existe $ENV_FILE — correr este script desde la raíz del repo en el servidor." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

echo "[$(date -Iseconds)] Iniciando backup de MinIO (bucket $MINIO_BUCKET) -> /backups/$TIMESTAMP"

docker compose -f "$COMPOSE_FILE" exec -T minio sh -c "
    mc alias set backupsrc http://localhost:9000 '$MINIO_ROOT_USER' '$MINIO_ROOT_PASSWORD' >/dev/null &&
    mc mirror --overwrite --quiet backupsrc/$MINIO_BUCKET /backups/$TIMESTAMP
"

echo "[$(date -Iseconds)] Backup completo"

echo "[$(date -Iseconds)] Eliminando backups de MinIO con más de $RETENCION_DIAS días"
docker compose -f "$COMPOSE_FILE" exec -T minio sh -c "
    find /backups -mindepth 1 -maxdepth 1 -type d -mtime +${RETENCION_DIAS} -print -exec rm -rf {} \;
"
