"""
POC: genera un reporte ejecutivo PDF end-to-end para un vuelo ya
procesado, sin pasar por ningún endpoint HTTP — corre el pipeline
completo (motor de diagnóstico + mapa PNG + template Jinja2 + WeasyPrint)
y escribe el resultado en disco para revisar el layout visualmente.

Uso (desde el contenedor api, que tiene weasyprint/jinja2/pillow):
    docker compose exec api python scripts/poc_reporte_pdf.py <lote_id> <vuelo_id>

<lote_id>/<vuelo_id> deben corresponder a un vuelo en estado 'completado'
con NDVI calculado — el mismo requisito que GET .../diagnostico.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.auth.models  # noqa: E402,F401 — registra Usuario en el registry declarativo antes de Lote.usuario
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.diagnostico.service import generar_diagnostico  # noqa: E402
from app.lotes.service import obtener_lote  # noqa: E402
from app.reportes.service import generar_pdf_reporte  # noqa: E402

OUTPUT = Path("reporte_poc.pdf")


async def main(lote_id: uuid.UUID, vuelo_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        lote = await obtener_lote(db, lote_id)
        if lote is None:
            sys.exit(f"Lote {lote_id} no encontrado.")

        diagnostico = await generar_diagnostico(db, lote, vuelo_id)
        if diagnostico is None:
            sys.exit(
                f"Diagnóstico no disponible para el vuelo {vuelo_id}. "
                "Debe estar en estado 'completado' y tener NDVI calculado."
            )
        await db.commit()  # generar_diagnostico solo hace flush() — igual que get_db()

    pdf_bytes = generar_pdf_reporte(diagnostico)
    OUTPUT.write_bytes(pdf_bytes)
    n_zonas = len(diagnostico.get("features", []))
    print(f"OK — {OUTPUT.resolve()} ({len(pdf_bytes) / 1024:.0f} KB, {n_zonas} zonas)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Uso: python {sys.argv[0]} <lote_id> <vuelo_id>")
    try:
        lote_id_arg = uuid.UUID(sys.argv[1])
        vuelo_id_arg = uuid.UUID(sys.argv[2])
    except ValueError:
        sys.exit("lote_id y vuelo_id deben ser UUID válidos.")

    asyncio.run(main(lote_id_arg, vuelo_id_arg))
