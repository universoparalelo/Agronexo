"""
Tests CRUD de lotes + soft delete.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_lotes.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_lotes.py -v
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL = f"lotes_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "lotes_pass_456"
_GEOM = {
    "type": "Polygon",
    "coordinates": [[
        [-60.6753, -27.4693],
        [-60.6701, -27.4693],
        [-60.6701, -27.4741],
        [-60.6753, -27.4741],
        [-60.6753, -27.4693],
    ]],
}

# "Bowtie" — las aristas A-B y C-D cruzan por el centro del rectángulo.
_GEOM_AUTOINTERSECTADA = {
    "type": "Polygon",
    "coordinates": [[
        [-60.70, -27.45],
        [-60.65, -27.50],
        [-60.70, -27.50],
        [-60.65, -27.45],
        [-60.70, -27.45],
    ]],
}

# ~0.01 ha — por debajo del mínimo (0.5 ha) esperado para un lote agrícola.
_GEOM_MUY_CHICA = {
    "type": "Polygon",
    "coordinates": [[
        [-60.6753, -27.4693],
        [-60.67520, -27.4693],
        [-60.67520, -27.46940],
        [-60.6753, -27.46940],
        [-60.6753, -27.4693],
    ]],
}

# ~1.000.000 ha — muy por encima del máximo (5000 ha) esperado para un lote agrícola.
_GEOM_MUY_GRANDE = {
    "type": "Polygon",
    "coordinates": [[
        [-61.0, -27.0],
        [-60.0, -27.0],
        [-60.0, -28.0],
        [-61.0, -28.0],
        [-61.0, -27.0],
    ]],
}

# El TestClient se abre en setup_module y se cierra en teardown_module para
# mantener el mismo event loop de anyio en todas las llamadas del módulo.
_tc = TestClient(app)
_token: str = ""


def setup_module(module):
    global _token
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={
        "email": _EMAIL, "nombre": "Test Lotes", "password": _PASS,
    })
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, f"setup_module login falló: {r.status_code} {r.text}"
    _token = r.json()["access_token"]
    print(f"\nUsuario de prueba: {_EMAIL}")


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token}"}


def _crear_lote(nombre: str = "Lote Test") -> dict:
    r = _tc.post("/api/v1/lotes", json={
        "nombre": nombre, "geometry": _GEOM,
    }, headers=_auth())
    assert r.status_code == 201, f"No se pudo crear lote auxiliar: {r.text}"
    return r.json()


def _crear_cultivo(lote_id: str, tipo: str = "soja", fecha_siembra: str | None = None) -> dict:
    r = _tc.post(f"/api/v1/lotes/{lote_id}/cultivos", json={
        "tipo_cultivo": tipo, "fecha_siembra": fecha_siembra,
    }, headers=_auth())
    assert r.status_code == 201, f"No se pudo crear cultivo auxiliar: {r.text}"
    return r.json()


def _insertar_vuelo(lote_id: str, estado: str = "completado", fecha_vuelo: datetime | None = None) -> str:
    """Inserta un vuelo directo en la BD (sin MinIO ni Celery) — mismo
    criterio que test_diagnostico_api.py / test_exportacion_api.py."""
    vuelo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO vuelos (id, lote_id, sensor, fecha_vuelo, estado, created_at) "
            "VALUES (CAST(:id AS uuid), CAST(:lote_id AS uuid), :sensor, :fecha, :estado, :created_at)"
        ), {
            "id": vuelo_id, "lote_id": lote_id, "sensor": "dji_mavic3",
            "fecha": fecha_vuelo or now, "estado": estado, "created_at": now,
        })
        conn.commit()
    engine.dispose()
    return vuelo_id


# ── Crear ─────────────────────────────────────────────────────────────

def test_crear_lote():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Norte Principal",
        "geometry": _GEOM,
    }, headers=_auth())
    assert r.status_code == 201
    body = r.json()
    assert body["nombre"] == "Lote Norte Principal"
    assert "cultivo" not in body and "variedad" not in body and "fecha_siembra" not in body
    assert body["cultivos"] == []
    assert body["geometry"] is not None
    assert body["area_ha"] is not None
    assert body["area_ha"] > 0
    print(f"✓ POST /lotes → 201, área={body['area_ha']:.2f} ha")


def test_crear_lote_sin_auth():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Sin Auth", "geometry": _GEOM,
    })
    assert r.status_code == 401
    print("✓ POST /lotes sin token → 401")


def test_crear_lote_geometry_invalida():
    geom_invalida = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]}
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Geom Rota", "geometry": geom_invalida,
    }, headers=_auth())
    assert r.status_code == 422
    print("✓ POST /lotes con geometry inválida → 422")


def test_crear_lote_geometry_autointersectada():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Bowtie", "geometry": _GEOM_AUTOINTERSECTADA,
    }, headers=_auth())
    assert r.status_code == 422
    print("✓ POST /lotes con geometry autointersectada (bowtie) → 422")


def test_crear_lote_area_muy_chica():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Diminuto", "geometry": _GEOM_MUY_CHICA,
    }, headers=_auth())
    assert r.status_code == 400
    print(f"✓ POST /lotes con área < 0.5 ha → 400 ({r.json()['detail']})")


def test_crear_lote_area_muy_grande():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Gigante", "geometry": _GEOM_MUY_GRANDE,
    }, headers=_auth())
    assert r.status_code == 400
    print(f"✓ POST /lotes con área > 5000 ha → 400 ({r.json()['detail']})")


def test_crear_lote_ignora_campos_de_cultivo():
    # cultivo/variedad/fecha_siembra/estadio ya no son del lote (viven en /cultivos)
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Con Campos Viejos", "cultivo": "soja", "variedad": "X",
        "fecha_siembra": "2026-11-15T00:00:00Z", "estadio_fenologico": "R2", "geometry": _GEOM,
    }, headers=_auth())
    assert r.status_code == 201
    assert "cultivo" not in r.json()
    print("✓ POST /lotes ignora campos de cultivo")


# ── Listar ────────────────────────────────────────────────────────────

def test_listar_lotes():
    lote = _crear_lote("Lote Para Listar")
    r = _tc.get("/api/v1/lotes", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1
    ids = [it["id"] for it in body["items"]]
    assert lote["id"] in ids
    print(f"✓ GET /lotes → 200, {body['total']} lote(s) en total")


def test_listar_lotes_sin_auth():
    r = _tc.get("/api/v1/lotes")
    assert r.status_code == 401
    print("✓ GET /lotes sin token → 401")


# ── Obtener ───────────────────────────────────────────────────────────

def test_obtener_lote_por_id():
    lote = _crear_lote("Lote Para GET")
    r = _tc.get(f"/api/v1/lotes/{lote['id']}", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == lote["id"]
    assert body["nombre"] == "Lote Para GET"
    print("✓ GET /lotes/{id} → 200")


def test_obtener_lote_inexistente():
    r = _tc.get(f"/api/v1/lotes/{uuid.uuid4()}", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /lotes/{uuid_random} → 404")


# ── Actualizar ────────────────────────────────────────────────────────

def test_actualizar_lote_nombre_y_suelo():
    lote = _crear_lote("Lote Original")
    r = _tc.put(f"/api/v1/lotes/{lote['id']}", json={
        "nombre": "Lote Actualizado",
        "tipo_suelo": "vertisol",
    }, headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["nombre"] == "Lote Actualizado"
    assert body["tipo_suelo"] == "vertisol"
    print("✓ PUT /lotes/{id} → 200 con nombre y tipo de suelo actualizados")


def test_actualizar_lote_agrega_geometry():
    lote = _crear_lote("Lote Sin Límites")
    r = _tc.put(f"/api/v1/lotes/{lote['id']}", json={
        "geometry": _GEOM,
    }, headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["geometry"] is not None
    assert body["area_ha"] is not None and body["area_ha"] > 0
    print(f"✓ PUT /lotes/{{id}} agrega límites → 200, área={body['area_ha']:.2f} ha")


def test_actualizar_lote_geometry_area_fuera_de_rango():
    lote = _crear_lote("Lote Para Editar Mal")
    r = _tc.put(f"/api/v1/lotes/{lote['id']}", json={
        "geometry": _GEOM_MUY_GRANDE,
    }, headers=_auth())
    assert r.status_code == 400
    print("✓ PUT /lotes/{id} con área fuera de rango → 400 (geometry original se mantiene)")


def test_actualizar_lote_inexistente():
    r = _tc.put(f"/api/v1/lotes/{uuid.uuid4()}", json={"nombre": "X"}, headers=_auth())
    assert r.status_code == 404
    print("✓ PUT /lotes/{uuid_random} → 404")


# ── Eliminar (soft delete) ────────────────────────────────────────────

def test_soft_delete_devuelve_204():
    lote = _crear_lote("Lote Para Borrar")
    r = _tc.delete(f"/api/v1/lotes/{lote['id']}", headers=_auth())
    assert r.status_code == 204
    print("✓ DELETE /lotes/{id} → 204")


def test_lote_borrado_no_accesible_por_get():
    lote = _crear_lote("Lote Borrado GET")
    _tc.delete(f"/api/v1/lotes/{lote['id']}", headers=_auth())

    r = _tc.get(f"/api/v1/lotes/{lote['id']}", headers=_auth())
    assert r.status_code == 404
    print("✓ GET lote eliminado → 404 (soft delete verificado)")


def test_lote_borrado_no_aparece_en_lista():
    lote = _crear_lote("Lote Efímero")
    lote_id = lote["id"]
    _tc.delete(f"/api/v1/lotes/{lote_id}", headers=_auth())

    items = _tc.get("/api/v1/lotes", headers=_auth()).json()["items"]
    ids = [it["id"] for it in items]
    assert lote_id not in ids
    print("✓ Lote eliminado no aparece en GET /lotes (soft delete)")


def test_delete_lote_inexistente():
    r = _tc.delete(f"/api/v1/lotes/{uuid.uuid4()}", headers=_auth())
    assert r.status_code == 404
    print("✓ DELETE /lotes/{uuid_random} → 404")


# ── Aislamiento por usuario ───────────────────────────────────────────

def test_lote_de_otro_usuario_no_accesible():
    email2 = f"otro_{uuid.uuid4().hex[:8]}@agronexo-test.com"
    _tc.post("/api/v1/auth/register", json={
        "email": email2, "nombre": "Otro Usuario", "password": "pass_otro_456",
    })
    token2 = _tc.post("/api/v1/auth/login", json={
        "email": email2, "password": "pass_otro_456",
    }).json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    lote_ajeno = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote de Otro", "geometry": _GEOM,
    }, headers=headers2).json()

    r = _tc.get(f"/api/v1/lotes/{lote_ajeno['id']}", headers=_auth())
    assert r.status_code == 404
    print("✓ Lote de otro usuario no es accesible → 404")


def test_lote_de_otro_usuario_no_aparece_en_lista():
    email3 = f"tercero_{uuid.uuid4().hex[:8]}@agronexo-test.com"
    _tc.post("/api/v1/auth/register", json={
        "email": email3, "nombre": "Tercero", "password": "pass_ter_789",
    })
    token3 = _tc.post("/api/v1/auth/login", json={
        "email": email3, "password": "pass_ter_789",
    }).json()["access_token"]

    lote_ajeno = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Privado", "geometry": _GEOM,
    }, headers={"Authorization": f"Bearer {token3}"}).json()

    items = _tc.get("/api/v1/lotes", headers=_auth()).json()["items"]
    ids = [it["id"] for it in items]
    assert lote_ajeno["id"] not in ids
    print("✓ Lote de otro usuario no aparece en GET /lotes del usuario actual")


# ── Regresión: tipos de Lote.usuario_id vs Usuario.id ───────────────────

def test_lote_usuario_carga_via_selectinload():
    """Usuario.id es str (as_uuid=False) — Lote.usuario_id tiene que matchear
    ese tipo Python o un eager load de la relación `usuario` queda en None en
    silencio (mismo bug real que tenía Vuelo.subido_por, ver HU-R4-02 en
    docs/release-v4.0.0.md). No se ejerce en ningún endpoint hoy, así que sin
    este test quedaría dormido de nuevo si alguien vuelve a romper el tipo."""
    import uuid as _uuid

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session, selectinload

    from app.core.config import settings
    from app.lotes.models import Lote

    lote = _crear_lote("Lote Para Test de Relación")

    engine = create_engine(settings.database_url_sync)
    with Session(engine) as session:
        stmt = select(Lote).options(selectinload(Lote.usuario)).where(Lote.id == _uuid.UUID(lote["id"]))
        cargado = session.execute(stmt).scalar_one()
        assert cargado.usuario is not None
        assert cargado.usuario.email == _EMAIL
    engine.dispose()
    print("✓ Lote.usuario carga correctamente vía selectinload (no None)")


# ── Listado: último vuelo, filtros y paginado (HU-R4-03) ────────────────

def test_listar_lotes_incluye_ultimo_vuelo_sin_consulta_extra():
    lote = _crear_lote("Lote Con Vuelos")
    _insertar_vuelo(lote["id"], "error", fecha_vuelo=datetime(2026, 1, 1, tzinfo=timezone.utc))
    vuelo_reciente = _insertar_vuelo(lote["id"], "completado", fecha_vuelo=datetime(2026, 6, 1, tzinfo=timezone.utc))

    r = _tc.get("/api/v1/lotes", headers=_auth())
    assert r.status_code == 200
    item = next(it for it in r.json()["items"] if it["id"] == lote["id"])
    assert item["ultimo_vuelo_estado"] == "completado"
    assert item["ultimo_vuelo_fecha"].startswith("2026-06-01")
    print("✓ GET /lotes trae el último vuelo (por fecha_vuelo) sin pedirlo aparte")


def test_listar_lotes_sin_vuelos_devuelve_null():
    lote = _crear_lote("Lote Sin Vuelos Para Listado")
    r = _tc.get("/api/v1/lotes", headers=_auth())
    item = next(it for it in r.json()["items"] if it["id"] == lote["id"])
    assert item["ultimo_vuelo_fecha"] is None
    assert item["ultimo_vuelo_estado"] is None
    print("✓ GET /lotes con lote sin vuelos → ultimo_vuelo_* en null")


def test_listar_lotes_filtro_busqueda_por_nombre():
    _crear_lote("Campo La Esperanza")
    _crear_lote("Campo El Progreso")
    r = _tc.get("/api/v1/lotes", params={"q": "Esperanza"}, headers=_auth())
    nombres = [it["nombre"] for it in r.json()["items"]]
    assert "Campo La Esperanza" in nombres
    assert "Campo El Progreso" not in nombres
    print("✓ GET /lotes?q= filtra por nombre")


def test_listar_lotes_filtro_estado():
    completado = _crear_lote("Lote Filtro Completado")
    _insertar_vuelo(completado["id"], "completado")
    pendiente = _crear_lote("Lote Filtro Pendiente")
    _insertar_vuelo(pendiente["id"], "pendiente")

    r = _tc.get("/api/v1/lotes", params={"estado": "completado"}, headers=_auth())
    ids = [it["id"] for it in r.json()["items"]]
    assert completado["id"] in ids
    assert pendiente["id"] not in ids
    print("✓ GET /lotes?estado= filtra por el estado del último análisis")


def test_listar_lotes_filtro_cultivo_y_campana():
    lote = _crear_lote("Lote Filtro Cultivo")
    _crear_cultivo(lote["id"], "maiz", fecha_siembra="2026-09-01T00:00:00Z")

    r = _tc.get("/api/v1/lotes", params={"cultivo": "maiz"}, headers=_auth())
    assert lote["id"] in [it["id"] for it in r.json()["items"]]
    r = _tc.get("/api/v1/lotes", params={"cultivo": "soja"}, headers=_auth())
    assert lote["id"] not in [it["id"] for it in r.json()["items"]]

    r = _tc.get("/api/v1/lotes", params={"campana": 2026}, headers=_auth())
    assert lote["id"] in [it["id"] for it in r.json()["items"]]
    r = _tc.get("/api/v1/lotes", params={"campana": 2020}, headers=_auth())
    assert lote["id"] not in [it["id"] for it in r.json()["items"]]
    print("✓ GET /lotes?cultivo=&campana= filtran por el cultivo actual del lote")


def test_listar_lotes_paginado():
    for i in range(3):
        _crear_lote(f"Lote Paginado {i}")
    r = _tc.get("/api/v1/lotes", params={"page_size": 1, "page": 1}, headers=_auth())
    body = r.json()
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert len(body["items"]) == 1
    assert body["total"] >= 3
    print("✓ GET /lotes?page=&page_size= pagina del lado del backend")


if __name__ == "__main__":
    setup_module(None)
    try:
        print("\n── CRUD Lotes + Soft Delete ─────────────────────────")
        test_crear_lote()
        test_crear_lote_sin_auth()
        test_crear_lote_geometry_invalida()
        test_crear_lote_geometry_autointersectada()
        test_crear_lote_area_muy_chica()
        test_crear_lote_area_muy_grande()
        test_crear_lote_ignora_campos_de_cultivo()
        test_listar_lotes()
        test_listar_lotes_sin_auth()
        test_obtener_lote_por_id()
        test_obtener_lote_inexistente()
        test_actualizar_lote_nombre_y_suelo()
        test_actualizar_lote_agrega_geometry()
        test_actualizar_lote_geometry_area_fuera_de_rango()
        test_actualizar_lote_inexistente()
        test_soft_delete_devuelve_204()
        test_lote_borrado_no_accesible_por_get()
        test_lote_borrado_no_aparece_en_lista()
        test_delete_lote_inexistente()
        test_lote_de_otro_usuario_no_accesible()
        test_lote_de_otro_usuario_no_aparece_en_lista()
        test_lote_usuario_carga_via_selectinload()
        test_listar_lotes_incluye_ultimo_vuelo_sin_consulta_extra()
        test_listar_lotes_sin_vuelos_devuelve_null()
        test_listar_lotes_filtro_busqueda_por_nombre()
        test_listar_lotes_filtro_estado()
        test_listar_lotes_filtro_cultivo_y_campana()
        test_listar_lotes_paginado()
        print("\nTodos los tests de lotes pasaron.\n")
    finally:
        teardown_module(None)
