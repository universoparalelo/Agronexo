#!/usr/bin/env bash
# Backup programado de Postgres (HU-R4-06). Pensado para correr vía cron en
# el host del servidor de producción, no dentro de ningún contenedor.
#
# Uso: ./scripts/backup_postgres.sh
# Cron sugerido (diario a las 3am, conserva los últimos 14 días):
#   0 3 * * * cd /ruta/al/repo && ./scripts/backup_postgres.sh >> backups/postgres/backup.log 2>&1

set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
BACKUP_DIR="backups/postgres"
RETENCION_DIAS=14

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: no existe $ENV_FILE — correr este script desde la raíz del repo en el servidor." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVO="$BACKUP_DIR/agronexo_${TIMESTAMP}.sql.gz"

echo "[$(date -Iseconds)] Iniciando backup de Postgres -> $ARCHIVO"

docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges \
    | gzip > "$ARCHIVO"

TAMANIO=$(du -h "$ARCHIVO" | cut -f1)
echo "[$(date -Iseconds)] Backup completo ($TAMANIO)"

echo "[$(date -Iseconds)] Eliminando backups de Postgres con más de $RETENCION_DIAS días"
find "$BACKUP_DIR" -name "agronexo_*.sql.gz" -mtime "+${RETENCION_DIAS}" -print -delete
