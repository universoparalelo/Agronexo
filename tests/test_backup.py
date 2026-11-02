"""
Tests de "Exportar todo" e "Importar" (app/backup/).

Trabajan en una base de datos propia que se crea y se borra en el módulo:
"reemplazar" borra todos los lotes, y eso no puede pasar en la base de desarrollo.
Los archivos van a una carpeta temporal con el almacenamiento en disco.

Necesitan Postgres con PostGIS (crean la base y corren alembic):
    docker compose exec api python3 -m pytest tests/test_backup.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_backup.py -v
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from unittest import mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.main import app

_BD = f"agronexo_bk_{uuid.uuid4().hex[:8]}"
_EMAIL = f"backup_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "backup_pass_123"
_RAIZ = Path(__file__).resolve().parent.parent
_POLIGONO = "POLYGON((-60.6753 -27.4693, -60.6701 -27.4693, -60.6701 -27.4741, -60.6753 -27.4741, -60.6753 -27.4693))"

_tc = TestClient(app)
_estado: dict = {}


def _url_bd(nombre: str, sincrona: bool = False) -> str:
    base = settings.database_url_sync if sincrona else settings.database_url
    return base.rsplit("/", 1)[0] + f"/{nombre}"


def setup_module(module):
    admin = create_engine(settings.database_url_sync, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{_BD}"'))
    admin.dispose()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_RAIZ, env={**os.environ, "POSTGRES_DB": _BD}, check=True, capture_output=True,
    )

    _estado["motor"] = create_async_engine(_url_bd(_BD), poolclass=NullPool)
    _estado["sync"] = create_engine(_url_bd(_BD, sincrona=True))

    async def _get_db():
        async with AsyncSession(_estado["motor"], expire_on_commit=False) as sesion:
            try:
                yield sesion
                await sesion.commit()
            except Exception:
                await sesion.rollback()
                raise

    app.dependency_overrides[get_db] = _get_db
    _estado["carpeta"] = Path(tempfile.mkdtemp(prefix="agronexo_bk_"))
    _estado["parches"] = [
        mock.patch.object(settings, "storage_backend", "disk"),
        mock.patch.object(settings, "storage_path", str(_estado["carpeta"] / "archivos")),
    ]
    for parche in _estado["parches"]:
        parche.start()

    _tc.__enter__()
    r = _tc.post("/api/v1/auth/register", json={"email": _EMAIL, "nombre": "Test Backup", "password": _PASS})
    assert r.status_code == 201, r.text
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    _estado["token"] = r.json()["access_token"]
    _estado["usuario_id"] = _tc.get("/api/v1/auth/me", headers=_auth()).json()["id"]


def teardown_module(module):
    _tc.__exit__(None, None, None)
    app.dependency_overrides.pop(get_db, None)
    for parche in _estado["parches"]:
        parche.stop()
    _estado["sync"].dispose()
    admin = create_engine(settings.database_url_sync, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{_BD}" WITH (FORCE)'))
    admin.dispose()
    shutil.rmtree(_estado["carpeta"], ignore_errors=True)


@pytest.fixture(autouse=True)
def _estado_limpio():
    _vaciar()
    shutil.rmtree(_estado["carpeta"] / "archivos", ignore_errors=True)
    shutil.rmtree(_estado["carpeta"] / "copias", ignore_errors=True)
    yield


def _auth() -> dict:
    return {"Authorization": f"Bearer {_estado['token']}"}


def _sql(consulta: str, **params):
    with _estado["sync"].begin() as conn:
        return conn.execute(text(consulta), params)


def _uno(consulta: str, **params):
    with _estado["sync"].connect() as conn:
        return conn.execute(text(consulta), params).scalar()


def _vaciar() -> None:
    for tabla in ("revisiones_diagnostico", "diagnosticos", "analisis_indices", "vuelos", "cultivos", "lotes"):
        _sql(f"DELETE FROM {tabla}")
    _sql("DELETE FROM precios_productos WHERE tipo = 'usuario'")


def _contar(tabla: str) -> int:
    return _uno(f"SELECT count(*) FROM {tabla}")


def _archivo(clave: str) -> Path:
    return _estado["carpeta"] / "archivos" / clave


def _escribir(clave: str, contenido: bytes) -> None:
    ruta = _archivo(clave)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)


def _sembrar(nombre: str = "Lote de prueba") -> dict:
    """Un lote completo: cultivo, vuelo con archivos, índice, diagnóstico, revisión y un precio."""
    ids = {k: str(uuid.uuid4()) for k in ("lote", "cultivo", "vuelo")}
    usuario = _estado["usuario_id"]
    base = f"{usuario}/{ids['lote']}/{ids['vuelo']}"
    ids["original"], ids["zonas"] = f"{base}/original.tif", f"{base}/zonas.geojson"
    _escribir(ids["original"], b"II*\x00" + os.urandom(2048))
    _escribir(ids["zonas"], b'{"type":"FeatureCollection","features":[]}')
    _sql(
        "INSERT INTO lotes (id, nombre, geometry, area_ha, usuario_id) VALUES "
        "(CAST(:l AS uuid), :n, ST_GeomFromText(:g, 4326), 25.1, CAST(:u AS uuid))",
        l=ids["lote"], n=nombre, g=_POLIGONO, u=usuario,
    )
    _sql("INSERT INTO cultivos (id, lote_id, tipo_cultivo, variedad) VALUES "
         "(CAST(:c AS uuid), CAST(:l AS uuid), 'soja', 'DM 50')", c=ids["cultivo"], l=ids["lote"])
    _sql(
        "INSERT INTO vuelos (id, lote_id, cultivo_id, fecha_vuelo, sensor, estado, archivo_original, "
        "geojson_key, subido_por_id, mapeo_bandas) VALUES (CAST(:v AS uuid), CAST(:l AS uuid), "
        "CAST(:c AS uuid), now(), 'dji_mavic3', 'completado', :o, :z, CAST(:u AS uuid), "
        "CAST(:m AS jsonb))",
        v=ids["vuelo"], l=ids["lote"], c=ids["cultivo"], o=ids["original"], z=ids["zonas"], u=usuario,
        m=json.dumps({"nir": 4, "red": 3}),
    )
    _sql("INSERT INTO analisis_indices (vuelo_id, indice, estado, geojson_key) VALUES "
         "(CAST(:v AS uuid), 'ndre', 'completado', :z)", v=ids["vuelo"], z=ids["zonas"])
    _sql("INSERT INTO diagnosticos (vuelo_id, resultado, motor_version) VALUES "
         "(CAST(:v AS uuid), CAST(:r AS jsonb), '1.2.0')",
         v=ids["vuelo"], r=json.dumps({"type": "FeatureCollection", "features": []}))
    _sql("INSERT INTO revisiones_diagnostico (vuelo_id, zona_id, regla_id, causa_sugerida, decision, "
         "evidencia, usuario_id) VALUES (CAST(:v AS uuid), 0, 'R20', 'estres_biotico_fungico', "
         "'aceptado', CAST(:e AS jsonb), CAST(:u AS uuid))",
         v=ids["vuelo"], e=json.dumps({"ndvi": 0.4}), u=usuario)
    ids["producto"] = _uno("SELECT id FROM productos_fitosanitarios ORDER BY nombre LIMIT 1")
    _sql("INSERT INTO precios_productos (producto_id, precio_usd, unidad, fecha, tipo) VALUES "
         "(CAST(:p AS uuid), 12.5, 'L', current_date, 'usuario')", p=str(ids["producto"]))
    return ids


def _exportar() -> bytes:
    r = _tc.post("/api/v1/backup/exportar", headers=_auth())
    assert r.status_code == 200, r.text
    descarga = _tc.get(r.json()["url_descarga"])
    assert descarga.status_code == 200
    return descarga.content


def _analizar(contenido: bytes):
    return _tc.post("/api/v1/backup/importar/analizar", headers=_auth(),
                    files={"archivo": ("backup.zip", contenido, "application/zip")})


def _importar(contenido: bytes, modo: str) -> dict:
    analisis = _analizar(contenido)
    assert analisis.status_code == 200, analisis.text
    r = _tc.post(f"/api/v1/backup/importar/{analisis.json()['importacion_id']}", json={"modo": modo}, headers=_auth())
    assert r.status_code == 200, r.text
    return r.json()


def _reescribir(contenido: bytes, transformar) -> bytes:
    """Devuelve el zip con cada miembro pasado por transformar(nombre, datos) -> (nombre, datos)."""
    salida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(contenido)) as origen, zipfile.ZipFile(salida, "w") as destino:
        for info in origen.infolist():
            nombre, datos = transformar(info.filename, origen.read(info))
            destino.writestr(nombre, datos)
    return salida.getvalue()


# ── Exportar ──────────────────────────────────────────────────────────

def test_exportar_incluye_datos_y_archivos():
    ids = _sembrar()
    with zipfile.ZipFile(io.BytesIO(_exportar())) as zf:
        nombres = set(zf.namelist())
        manifiesto = json.loads(zf.read("manifiesto.json"))
        perfil = zf.read("datos/perfil.json").decode()
    assert {"manifiesto.json", "datos/lotes.jsonl", "datos/perfil.json"} <= nombres
    assert f"archivos/{ids['original']}" in nombres and f"archivos/{ids['zonas']}" in nombres
    assert manifiesto["conteos"]["lotes"] == 1 and manifiesto["conteos"]["vuelos"] == 1
    assert manifiesto["conteos"]["precios_productos"] == 1
    assert manifiesto["archivos"] == 2 and manifiesto["archivos_faltantes"] == []
    assert "hashed_password" not in perfil and _EMAIL not in perfil


def test_exportar_anota_los_archivos_que_faltan():
    ids = _sembrar()
    _archivo(ids["original"]).unlink()
    with zipfile.ZipFile(io.BytesIO(_exportar())) as zf:
        manifiesto = json.loads(zf.read("manifiesto.json"))
    assert manifiesto["archivos_faltantes"] == [ids["original"]]


def test_sin_sesion_no_se_puede_exportar():
    assert _tc.post("/api/v1/backup/exportar").status_code == 401


def test_descarga_con_enlace_invalido():
    assert _tc.get("/api/v1/backup/descargas/no-es-un-token").status_code == 401


# ── Reemplazar ────────────────────────────────────────────────────────

def test_reemplazar_recupera_lo_borrado():
    ids = _sembrar()
    geometria = _uno("SELECT ST_AsText(geometry) FROM lotes")
    backup = _exportar()
    _vaciar()
    shutil.rmtree(_estado["carpeta"] / "archivos")

    resumen = _importar(backup, "reemplazar")

    assert resumen["tablas"]["lotes"]["insertados"] == 1
    assert _uno("SELECT id::text FROM lotes") == ids["lote"]
    assert _uno("SELECT ST_AsText(geometry) FROM lotes") == geometria
    assert _uno("SELECT mapeo_bandas->>'nir' FROM vuelos") == "4"
    assert _contar("cultivos") == _contar("analisis_indices") == _contar("diagnosticos") == 1
    assert _contar("revisiones_diagnostico") == 1
    assert _uno("SELECT producto_id::text FROM precios_productos WHERE tipo = 'usuario'") == str(ids["producto"])
    assert _archivo(ids["original"]).stat().st_size > 2000
    assert resumen["archivos"]["copiados"] == 2


def test_reemplazar_guarda_antes_una_copia_de_lo_actual():
    _sembrar()
    resumen = _importar(_exportar(), "reemplazar")
    copia = _estado["carpeta"] / "copias" / resumen["copia_previa"]
    assert copia.is_file() and zipfile.is_zipfile(copia)


def test_reemplazar_quita_lo_que_no_estaba_en_el_backup():
    primero = _sembrar("Primero")
    backup = _exportar()
    segundo = _sembrar("Segundo")

    _importar(backup, "reemplazar")

    assert _contar("lotes") == 1 and _uno("SELECT nombre FROM lotes") == "Primero"
    assert _archivo(primero["original"]).is_file()
    assert not _archivo(segundo["original"]).exists()


def test_reemplazar_reasigna_los_datos_al_usuario_de_esta_instalacion():
    ids = _sembrar()
    otro = str(uuid.uuid4())
    reasignado = _reescribir(
        _exportar(),
        lambda n, d: (n.replace(_estado["usuario_id"], otro), d.replace(_estado["usuario_id"].encode(), otro.encode())),
    )
    _vaciar()
    shutil.rmtree(_estado["carpeta"] / "archivos")

    _importar(reasignado, "reemplazar")

    assert _uno("SELECT usuario_id::text FROM lotes") == _estado["usuario_id"]
    assert _uno("SELECT subido_por_id::text FROM vuelos") == _estado["usuario_id"]
    assert _uno("SELECT usuario_id::text FROM revisiones_diagnostico") == _estado["usuario_id"]
    clave = f"{_estado['usuario_id']}/{ids['lote']}/{ids['vuelo']}/original.tif"
    assert _uno("SELECT archivo_original FROM vuelos") == clave and _archivo(clave).is_file()


def test_reemplazar_busca_el_producto_por_nombre_y_no_por_id():
    ids = _sembrar()
    cambiado = _reescribir(
        _exportar(),
        lambda n, d: (n, d.replace(str(ids["producto"]).encode(), str(uuid.uuid4()).encode())
                      if n == "datos/precios_productos.jsonl" else d),
    )
    _vaciar()
    _importar(cambiado, "reemplazar")
    assert _uno("SELECT producto_id::text FROM precios_productos WHERE tipo = 'usuario'") == str(ids["producto"])


# ── Sumar ─────────────────────────────────────────────────────────────

def test_sumar_agrega_lo_que_falta_y_conserva_lo_local():
    a = _sembrar("A")
    backup = _exportar()
    _vaciar()
    shutil.rmtree(_estado["carpeta"] / "archivos")
    b = _sembrar("B")

    resumen = _importar(backup, "sumar")

    assert sorted(_sql("SELECT nombre FROM lotes").scalars().all()) == ["A", "B"]
    assert resumen["tablas"]["lotes"] == {"insertados": 1, "actualizados": 0, "omitidos": 0}
    assert _archivo(a["original"]).is_file() and _archivo(b["original"]).is_file()
    assert resumen["copia_previa"] is None


def test_sumar_dos_veces_no_duplica():
    _sembrar()
    backup = _exportar()
    resumen = _importar(backup, "sumar")
    assert all(c["insertados"] == 0 and c["actualizados"] == 0 for c in resumen["tablas"].values())
    assert resumen["archivos"] == {"copiados": 0, "omitidos": 2, "faltantes": 0}
    for tabla in ("lotes", "cultivos", "vuelos", "analisis_indices", "diagnosticos", "revisiones_diagnostico"):
        assert _contar(tabla) == 1
    assert _uno("SELECT count(*) FROM precios_productos WHERE tipo = 'usuario'") == 1


def test_sumar_gana_el_lote_modificado_mas_recientemente():
    _sembrar("Original")
    backup = _exportar()

    _sql("UPDATE lotes SET nombre = 'Local viejo', updated_at = now() - interval '1 day'")
    resumen = _importar(backup, "sumar")
    assert _uno("SELECT nombre FROM lotes") == "Original"
    assert resumen["tablas"]["lotes"]["actualizados"] == 1

    _sql("UPDATE lotes SET nombre = 'Local nuevo', updated_at = now() + interval '1 hour'")
    resumen = _importar(backup, "sumar")
    assert _uno("SELECT nombre FROM lotes") == "Local nuevo"
    assert resumen["tablas"]["lotes"]["omitidos"] == 1


def test_sumar_gana_el_diagnostico_calculado_mas_recientemente():
    _sembrar()
    backup = _exportar()
    _sql("UPDATE diagnosticos SET resultado = CAST('{\"local\": true}' AS jsonb), "
         "calculado_en = now() - interval '1 day'")
    _importar(backup, "sumar")
    assert _uno("SELECT resultado ? 'features' FROM diagnosticos") is True
    assert _contar("diagnosticos") == 1


def test_sumar_la_revision_mas_nueva_de_la_misma_zona_reemplaza_a_la_vieja():
    _sembrar()
    backup = _exportar()
    _sql("UPDATE revisiones_diagnostico SET decision = 'rechazado', id = uuid_generate_v4(), "
         "updated_at = now() - interval '1 day'")
    _importar(backup, "sumar")
    assert _contar("revisiones_diagnostico") == 1
    assert _uno("SELECT decision::text FROM revisiones_diagnostico") == "aceptado"


def test_sumar_da_de_baja_lo_que_se_dio_de_baja_en_el_backup():
    _sembrar()
    _sql("UPDATE vuelos SET deleted_at = now()")
    backup = _exportar()
    _sql("UPDATE vuelos SET deleted_at = NULL")
    resumen = _importar(backup, "sumar")
    assert _uno("SELECT deleted_at IS NOT NULL FROM vuelos") is True
    assert resumen["tablas"]["vuelos"]["actualizados"] == 1


def test_sumar_no_pisa_el_perfil_que_ya_esta_completo():
    _sembrar()
    _sql("UPDATE usuarios SET nombre_empresa = 'Empresa del backup' WHERE id = CAST(:u AS uuid)", u=_estado["usuario_id"])
    backup = _exportar()
    _sql("UPDATE usuarios SET nombre_empresa = 'Empresa local' WHERE id = CAST(:u AS uuid)", u=_estado["usuario_id"])
    _importar(backup, "sumar")
    assert _uno("SELECT nombre_empresa FROM usuarios WHERE id = CAST(:u AS uuid)", u=_estado["usuario_id"]) == "Empresa local"
    _importar(backup, "reemplazar")
    assert _uno("SELECT nombre_empresa FROM usuarios WHERE id = CAST(:u AS uuid)", u=_estado["usuario_id"]) == "Empresa del backup"


# ── Avisos y errores ──────────────────────────────────────────────────

def test_avisa_si_el_backup_es_de_una_version_mas_nueva_pero_deja_importar():
    _sembrar()

    def subir_revision(nombre, datos):
        if nombre == "manifiesto.json":
            manifiesto = json.loads(datos)
            manifiesto["revision_base"] = "9999"
            datos = json.dumps(manifiesto).encode()
        return nombre, datos

    nuevo = _reescribir(_exportar(), subir_revision)
    analisis = _analizar(nuevo).json()
    assert [a["codigo"] for a in analisis["advertencias"]] == ["version_mas_nueva"]
    _importar(nuevo, "sumar")


def test_ignora_y_avisa_los_campos_que_esta_version_no_conoce():
    _sembrar()

    def agregar_campo(nombre, datos):
        if nombre == "datos/lotes.jsonl":
            fila = json.loads(datos)
            fila["campo_del_futuro"] = 1
            datos = json.dumps(fila).encode()
        return nombre, datos

    nuevo = _reescribir(_exportar(), agregar_campo)
    avisos = _analizar(nuevo).json()["advertencias"]
    assert [(a["codigo"], "campo_del_futuro" in a["mensaje"]) for a in avisos] == [("columnas_desconocidas", True)]
    _vaciar()
    resumen = _importar(nuevo, "reemplazar")
    assert resumen["columnas_desconocidas"] == {"lotes": ["campo_del_futuro"]}
    assert _contar("lotes") == 1


def test_un_backup_viejo_sin_columnas_nuevas_se_importa_con_los_valores_por_defecto():
    _sembrar()

    def quitar_columna(nombre, datos):
        if nombre == "datos/vuelos.jsonl":
            fila = json.loads(datos)
            del fila["mapeo_bandas"], fila["estado"]
            datos = json.dumps(fila).encode()
        return nombre, datos

    viejo = _reescribir(_exportar(), quitar_columna)
    _vaciar()
    _importar(viejo, "reemplazar")
    assert _uno("SELECT mapeo_bandas IS NULL FROM vuelos") is True
    assert _uno("SELECT estado::text FROM vuelos") == "pendiente"


def test_analizar_cuenta_lo_que_hay_hoy_en_la_app():
    _sembrar()
    analisis = _analizar(_exportar()).json()
    assert analisis["datos_actuales"] == {"lotes": 1, "vuelos": 1}
    assert analisis["conteos"]["lotes"] == 1


def test_un_archivo_que_no_es_backup_da_400():
    r = _analizar(b"esto no es un zip")
    assert r.status_code == 400
    assert not list((_estado["carpeta"] / "copias").glob("importacion-*.zip"))


def test_un_formato_mas_nuevo_da_400():
    def formato(nombre, datos):
        if nombre == "manifiesto.json":
            manifiesto = json.loads(datos)
            manifiesto["formato"] = 99
            datos = json.dumps(manifiesto).encode()
        return nombre, datos

    r = _analizar(_reescribir(_exportar(), formato))
    assert r.status_code == 400 and "Actualizá" in r.json()["detail"]


def test_importar_con_un_modo_invalido_da_422():
    analisis = _analizar(_exportar()).json()
    r = _tc.post(f"/api/v1/backup/importar/{analisis['importacion_id']}", json={"modo": "mezclar"}, headers=_auth())
    assert r.status_code == 422


def test_importar_algo_que_no_existe_da_404():
    r = _tc.post(f"/api/v1/backup/importar/{uuid.uuid4()}", json={"modo": "sumar"}, headers=_auth())
    assert r.status_code == 404
    assert _tc.post("/api/v1/backup/importar/no-es-un-id", json={"modo": "sumar"}, headers=_auth()).status_code == 404


def test_cancelar_borra_el_archivo_subido():
    importacion_id = _analizar(_exportar()).json()["importacion_id"]
    assert _tc.delete(f"/api/v1/backup/importar/{importacion_id}", headers=_auth()).status_code == 204
    r = _tc.post(f"/api/v1/backup/importar/{importacion_id}", json={"modo": "sumar"}, headers=_auth())
    assert r.status_code == 404


def test_si_la_importacion_falla_no_se_pierde_nada():
    ids = _sembrar()
    backup = _exportar()

    def romper(nombre, datos):
        if nombre == "datos/vuelos.jsonl":
            fila = json.loads(datos)
            fila["lote_id"] = str(uuid.uuid4())
            datos = json.dumps(fila).encode()
        return nombre, datos

    r_analisis = _analizar(_reescribir(backup, romper)).json()
    r = _tc.post(f"/api/v1/backup/importar/{r_analisis['importacion_id']}", json={"modo": "reemplazar"}, headers=_auth())
    assert r.status_code == 500
    assert _uno("SELECT id::text FROM lotes") == ids["lote"] and _contar("vuelos") == 1
    assert _archivo(ids["original"]).is_file()
