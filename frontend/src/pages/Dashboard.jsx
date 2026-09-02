import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useVueloProgreso } from '../hooks/useVueloProgreso'
import client from '../api/client'
import { eliminarVuelo, listarIndicesVuelo, reintentarVuelo } from '../api/analisis'
import BarraProgreso from '../components/BarraProgreso'
import MapaIndice from '../components/MapaIndice'
import ModalCargaGeoTIFF from '../components/ModalCargaGeoTIFF'
import ModalNuevoLote from '../components/ModalNuevoLote'
import ModalLimites from '../components/ModalLimites'
import ModalConfirmarEliminar from '../components/ModalConfirmarEliminar'
import SidebarNav from '../components/SidebarNav'

/* ──────── Icons ──────── */
const IconLotes = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
    <line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
  </svg>
)
const IconCargar = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
    <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
  </svg>
)
const IconDiagnostico = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
  </svg>
)
const IconInformes = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
    <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
  </svg>
)
const IconConfig = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
  </svg>
)
const IconBell = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
    <path d="M13.73 21a2 2 0 01-3.46 0"/>
  </svg>
)
const IconCalendar = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
)
const IconArrow = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
  </svg>
)
const IconZoom = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
)
const IconMap = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
    <line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
  </svg>
)
const IconTrash = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
  </svg>
)
const IconRetry = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="1 4 1 10 7 10"/>
    <path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>
  </svg>
)
const IconExpandir = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 3 21 3 21 9"/>
    <polyline points="9 21 3 21 3 15"/>
    <line x1="21" y1="3" x2="14" y2="10"/>
    <line x1="3" y1="21" x2="10" y2="14"/>
  </svg>
)
const IconContraer = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="4 14 10 14 10 20"/>
    <polyline points="20 10 14 10 14 4"/>
    <line x1="14" y1="10" x2="21" y2="3"/>
    <line x1="3" y1="21" x2="10" y2="14"/>
  </svg>
)

/* ──────── Helpers ──────── */
const CULTIVO_LABEL = { soja: 'Soja', maiz: 'Maíz', algodon: 'Algodón', sorgo: 'Sorgo' }

const ESTADO_BADGE = {
  completado: { label: 'Completado', cls: 'badge-optimo' },
  procesando: { label: 'Procesando', cls: 'badge-procesando' },
  pendiente:  { label: 'Pendiente',  cls: 'badge-procesando' },
  error:      { label: 'Error',      cls: 'badge-critico' },
}

function fmtFecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function fmtFechaHoy() {
  return new Date().toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

function fmtTiempoRelativo(fecha) {
  const diff = Date.now() - fecha.getTime()
  const mins = Math.floor(diff / 60000)
  const horas = Math.floor(diff / 3600000)
  const dias = Math.floor(diff / 86400000)
  if (mins < 1) return 'Justo ahora'
  if (mins < 60) return `Hace ${mins} min`
  if (horas < 24) return `Hace ${horas}h`
  if (dias === 1) return 'Ayer'
  if (dias < 7) return `Hace ${dias} días`
  return fmtFecha(fecha.toISOString())
}

function buildActivityFeed(loteRows, vueloRows, userName) {
  const items = []

  items.push({
    tipo: 'user',
    texto: `Sesión iniciada por ${userName}`,
    fecha: new Date(),
  })

  for (const lote of loteRows) {
    if (lote.created_at) {
      items.push({
        tipo: 'ok',
        texto: `Lote "${lote.nombre}" registrado`,
        fecha: new Date(lote.created_at),
      })
    }
  }

  for (const v of vueloRows) {
    const nombre = v.lote?.nombre || 'Lote'
    const fecha = new Date(v.created_at)
    if (v.estado === 'completado') {
      items.push({ tipo: 'ok', texto: `Análisis completado en ${nombre}`, fecha })
    } else if (v.estado === 'error') {
      items.push({ tipo: 'alerta', texto: `Error en análisis de ${nombre}`, fecha })
    } else if (v.estado === 'procesando') {
      items.push({ tipo: 'upload', texto: `Procesando análisis en ${nombre}`, fecha })
    } else {
      items.push({ tipo: 'upload', texto: `Ortomosaico cargado en ${nombre}`, fecha })
    }
  }

  items.sort((a, b) => b.fecha - a.fecha)
  return items.slice(0, 6)
}


/* ──────── KPI Card ──────── */
function KpiCard({ label, value, delta, deltaType, icon, highlight }) {
  return (
    <div className={`kpi-card${highlight ? ' kpi-card--highlight' : ''}`}>
      <div className="kpi-card-top">
        <span className="kpi-label">{label}</span>
        <span className="kpi-icon">{icon}</span>
      </div>
      <div className="kpi-value">{value}</div>
      {delta && <div className={`kpi-delta kpi-delta--${deltaType ?? 'up'}`}>{delta}</div>}
    </div>
  )
}

/* ──────── Mapa de análisis (panel inferior) ──────── */
const INDICE_LABEL = { ndvi: 'NDVI', ndre: 'NDRE', savi: 'SAVI', exg: 'ExG' }

function AnalisisMap({ loteId, vueloId, indice }) {
  const { estado, geojson, errorMsg } = useVueloProgreso(loteId, vueloId, indice)

  if (!estado) return <p className="estado-msg" style={{ padding: '1rem' }}>Cargando análisis...</p>

  const estadoActual = estado.estado
  if (estadoActual === 'completado' && geojson) return <MapaIndice geojson={geojson} />
  if (estadoActual === 'error' || errorMsg) {
    return (
      <p className="estado-msg" style={{ padding: '1rem', color: '#b91c1c' }}>
        {errorMsg || estado?.error || 'Error en el procesamiento.'}
      </p>
    )
  }
  return (
    <div style={{ padding: '1rem' }}>
      <BarraProgreso progreso={estado?.progreso ?? 0} mensaje={estado?.mensaje} estado={estadoActual} />
    </div>
  )
}

/* ──────── Dashboard ──────── */
export default function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [loteRows, setLoteRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [showModalNuevoLote, setShowModalNuevoLote] = useState(false)
  const [loteParaLimites, setLoteParaLimites] = useState(null)
  const [analisisParaEliminar, setAnalisisParaEliminar] = useState(null)
  const [reintentandoId, setReintentandoId] = useState(null)
  const [tablaError, setTablaError] = useState('')
  const [selectedVuelo, setSelectedVuelo] = useState(null)
  const [indicesDisponibles, setIndicesDisponibles] = useState([])
  const [mapaExpandido, setMapaExpandido] = useState(false)
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 4

  useEffect(() => {
    if (!mapaExpandido) return
    function onKeyDown(e) {
      if (e.key === 'Escape') setMapaExpandido(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [mapaExpandido])

  const cargarDatos = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await client.get('/lotes')
      const lotes = data.items ?? []
      const results = await Promise.allSettled(
        lotes.map(l => client.get(`/lotes/${l.id}/vuelos`))
      )
      setLoteRows(lotes.map((l, i) => ({
        ...l,
        vuelos: results[i].status === 'fulfilled' ? (results[i].value.data ?? []) : [],
      })))
    } catch {
      setLoteRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { cargarDatos() }, [cargarDatos])

  useEffect(() => {
    if (!selectedVuelo) { setIndicesDisponibles([]); return }
    let cancelado = false
    listarIndicesVuelo(selectedVuelo.loteId, selectedVuelo.vueloId)
      .then((data) => { if (!cancelado) setIndicesDisponibles(data) })
      .catch(() => { if (!cancelado) setIndicesDisponibles([]) })
    return () => { cancelado = true }
  }, [selectedVuelo?.loteId, selectedVuelo?.vueloId])

  function cambiarIndice(indice) {
    setSelectedVuelo((prev) => prev && { ...prev, indice })
  }

  function handleCargaExitosa(data) {
    setShowModal(false)
    cargarDatos()
    setSelectedVuelo({ loteId: data.lote_id, vueloId: data.vuelo_id, indice: 'ndvi' })
  }

  function handleNuevoLoteExitoso() {
    setShowModalNuevoLote(false)
    cargarDatos()
  }

  async function handleEliminarAnalisis() {
    const { loteId, vueloId } = analisisParaEliminar
    await eliminarVuelo(loteId, vueloId)
    setAnalisisParaEliminar(null)
    if (selectedVuelo?.vueloId === vueloId) setSelectedVuelo(null)
    cargarDatos()
  }

  async function handleReintentar(v) {
    setTablaError('')
    setReintentandoId(v.vueloId)
    try {
      await reintentarVuelo(v.lote.id, v.vueloId)
      await cargarDatos()
      setSelectedVuelo({ loteId: v.lote.id, vueloId: v.vueloId, indice: 'ndvi' })
    } catch (err) {
      setTablaError(err.response?.data?.detail || 'Error al reintentar el análisis.')
    } finally {
      setReintentandoId(null)
    }
  }

  const vueloRows = loteRows
    .flatMap(l => l.vuelos.map(v => ({ ...v, vueloId: v.vuelo_id ?? v.id, lote: l })))
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  const totalPages = Math.max(1, Math.ceil(vueloRows.length / PAGE_SIZE))
  const pageRows    = vueloRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const selectedVueloRow = vueloRows.find(v => v.vueloId === selectedVuelo?.vueloId)

  return (
    <div className="dashboard">
      {showModal && (
        <ModalCargaGeoTIFF
          lotes={loteRows}
          loteIdInicial={selectedVuelo?.loteId ?? null}
          onSuccess={handleCargaExitosa}
          onClose={() => setShowModal(false)}
        />
      )}
      {showModalNuevoLote && (
        <ModalNuevoLote onSuccess={handleNuevoLoteExitoso} onClose={() => setShowModalNuevoLote(false)} />
      )}
      {loteParaLimites && (
        <ModalLimites
          lote={loteParaLimites}
          onSuccess={() => { setLoteParaLimites(null); cargarDatos() }}
          onClose={() => setLoteParaLimites(null)}
        />
      )}
      {analisisParaEliminar && (
        <ModalConfirmarEliminar
          titulo="Eliminar diagnóstico"
          mensaje={`¿Seguro que querés eliminar el vuelo de "${analisisParaEliminar.etiqueta}"? Esta acción no se puede deshacer.`}
          onConfirmar={handleEliminarAnalisis}
          onClose={() => setAnalisisParaEliminar(null)}
        />
      )}

      <SidebarNav user={user} onCargarOrtomosaico={() => setShowModal(true)} />

      <div className="dashboard-body">
        {/* Topbar */}
        <header className="topbar">
          <nav className="topbar-breadcrumb">
            <span>Dashboard</span>
            <span className="breadcrumb-sep">›</span>
            <span className="breadcrumb-active">Resumen</span>
          </nav>
          <div className="topbar-actions">
            <button className="topbar-icon-btn" title="Notificaciones">
              <IconBell />
            </button>
            <div className="topbar-date">
              <IconCalendar />
              <span>{fmtFechaHoy()}</span>
            </div>
            <button className="btn-salir" onClick={() => { logout(); navigate('/login') }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
                <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              Salir
            </button>
          </div>
        </header>

        <main className="dashboard-main">
          {/* Welcome */}
          <div className="welcome-section">
            <h1 className="welcome-title">
              Bienvenido, {user?.nombre?.split(' ')[0] ?? 'Usuario'} 👋
            </h1>
            <p className="welcome-sub">
              Resumen del estado de tus cultivos y análisis recientes en la región de Chaco.
            </p>
          </div>

          {/* KPI cards */}
          <div className="kpi-row">
            <KpiCard
              label="LOTES REGISTRADOS"
              value={loteRows.length || '—'}
              delta={loteRows.length > 0 ? `${loteRows.length} activo${loteRows.length !== 1 ? 's' : ''}` : null}
              deltaType="up"
              icon={<IconLotes />}
            />
            <KpiCard
              label="ANÁLISIS REALIZADOS"
              value={vueloRows.length || '—'}
              delta={vueloRows.filter(v => v.estado === 'completado').length > 0 ? `${vueloRows.filter(v => v.estado === 'completado').length} completados` : null}
              deltaType="up"
              icon={<IconDiagnostico />}
            />
            <KpiCard
              label="ANÁLISIS COMPLETADOS"
              value={vueloRows.filter(v => v.estado === 'completado').length || '—'}
              delta={vueloRows.some(v => v.estado === 'completado') ? 'Con diagnóstico disponible' : 'Sin análisis aún'}
              deltaType={vueloRows.some(v => v.estado === 'completado') ? 'up' : 'neutral'}
              icon={<IconInformes />}
            />
            <KpiCard
              label="ÁREA MONITOREADA"
              value={loteRows.reduce((s, l) => s + (l.area_ha || 0), 0) > 0 ? `${Math.round(loteRows.reduce((s, l) => s + (l.area_ha || 0), 0))}` : '—'}
              delta={loteRows.reduce((s, l) => s + (l.area_ha || 0), 0) > 0 ? 'hectáreas totales' : 'Registrá un lote para comenzar'}
              deltaType={loteRows.reduce((s, l) => s + (l.area_ha || 0), 0) > 0 ? 'up' : 'neutral'}
              icon={<IconConfig />}
              highlight={loteRows.reduce((s, l) => s + (l.area_ha || 0), 0) > 0}
            />
          </div>

          {/* Grid principal */}
          <div className="dashboard-grid">
            {/* Columna izquierda */}
            <div className="dashboard-col-main">
              {/* Tabla análisis recientes */}
              <div className="card">
                <div className="card-header">
                  <div>
                    <h2 className="card-title">Análisis Recientes</h2>
                    <p className="card-sub">Últimos vuelos procesados y estado de vigor</p>
                  </div>
                  <button className="card-link">Ver todos <IconArrow /></button>
                </div>
                {tablaError && (
                  <div className="error-message" style={{ margin: '0 1.1rem 0.75rem' }}>{tablaError}</div>
                )}
                <div className="card-body" style={{ padding: '0' }}>
                  {loading ? (
                    <p className="estado-msg" style={{ padding: '1rem 1.1rem' }}>Cargando...</p>
                  ) : loteRows.length === 0 ? (
                    <div className="empty-state">
                      <p>No hay lotes registrados.</p>
                      <p className="empty-hint">Creá un lote para comenzar.</p>
                    </div>
                  ) : vueloRows.length === 0 ? (
                    <div className="empty-state">
                      <p>No hay vuelos cargados todavía.</p>
                      <p className="empty-hint">Usá "Cargar Ortomosaico" para subir el primer vuelo de un lote.</p>
                    </div>
                  ) : (
                    <>
                      <table className="analisis-table">
                        <thead>
                          <tr>
                            <th>LOTE</th>
                            <th>FECHA</th>
                            <th>ESTADO</th>
                            <th>ACCIÓN</th>
                          </tr>
                        </thead>
                        <tbody>
                          {pageRows.map(v => {
                            const badge = ESTADO_BADGE[v.estado] ?? { label: v.estado, cls: 'badge-procesando' }
                            return (
                              <tr key={v.vueloId} className={selectedVuelo?.vueloId === v.vueloId ? 'tr--active' : ''}>
                                <td>
                                  <div className="td-lote-nombre">{v.lote.nombre}</div>
                                  <div className="td-lote-info">
                                    {CULTIVO_LABEL[v.lote.cultivo] ?? v.lote.cultivo}
                                    {v.lote.area_ha ? ` · ${Math.round(v.lote.area_ha)} ha` : ''}
                                  </div>
                                </td>
                                <td className="td-fecha">{fmtFecha(v.created_at)}</td>
                                <td>
                                  <span className={`table-badge ${badge.cls}`}>{badge.label}</span>
                                </td>
                                <td>
                                  <div className="td-acciones">
                                    <button
                                      className="tbl-btn"
                                      title="Ver análisis"
                                      onClick={() => setSelectedVuelo({ loteId: v.lote.id, vueloId: v.vueloId, indice: 'ndvi' })}
                                    >
                                      <IconZoom />
                                    </button>
                                    <button
                                      className="tbl-btn"
                                      title="Límites"
                                      onClick={() => setLoteParaLimites(v.lote)}
                                    >
                                      <IconMap />
                                    </button>
                                    {v.estado === 'error' && (
                                      <button
                                        className="tbl-btn tbl-btn--retry"
                                        title="Reintentar análisis"
                                        disabled={reintentandoId === v.vueloId}
                                        onClick={() => handleReintentar(v)}
                                      >
                                        <IconRetry />
                                      </button>
                                    )}
                                    <button
                                      className="tbl-btn tbl-btn--danger"
                                      title="Eliminar diagnóstico"
                                      onClick={() => setAnalisisParaEliminar({
                                        loteId: v.lote.id,
                                        vueloId: v.vueloId,
                                        etiqueta: `${v.lote.nombre} · ${fmtFecha(v.created_at)}`,
                                      })}
                                    >
                                      <IconTrash />
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                      <div className="table-footer">
                        <span>Mostrando {pageRows.length} de {vueloRows.length} vuelos</span>
                        <div className="pagination">
                          <button className="page-btn" disabled={page === 1} onClick={() => setPage(p => p - 1)}>‹</button>
                          <span>Página {page} de {totalPages}</span>
                          <button className="page-btn" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>›</button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Vista geoespacial */}
              {mapaExpandido && <div className="mapa-expand-backdrop" onClick={() => setMapaExpandido(false)} />}
              <div className={`card card--mapa${mapaExpandido ? ' card--mapa-expandido' : ''}`}>
                <div className="card-header">
                  <div>
                    <h2 className="card-title">📍 Vista geoespacial</h2>
                    <p className="card-sub">
                      {selectedVuelo
                        ? (selectedVueloRow
                            ? `Análisis — ${selectedVueloRow.lote.nombre} · ${fmtFecha(selectedVueloRow.created_at)}`
                            : 'Análisis en curso')
                        : 'Mapa de lotes registrados en la zona norte'}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                    {selectedVuelo && (
                      <button
                        className="card-link"
                        onClick={() => setMapaExpandido((v) => !v)}
                        title={mapaExpandido ? 'Contraer mapa' : 'Expandir mapa'}
                      >
                        {mapaExpandido ? <IconContraer /> : <IconExpandir />}
                        {mapaExpandido ? 'Contraer' : 'Expandir'}
                      </button>
                    )}
                    {selectedVuelo && (
                      <button className="card-link" onClick={() => { setSelectedVuelo(null); setMapaExpandido(false) }}>
                        Cerrar ×
                      </button>
                    )}
                  </div>
                </div>
                {selectedVuelo && indicesDisponibles.length > 1 && (
                  <div className="indice-switcher">
                    {indicesDisponibles.map((i) => (
                      <button
                        type="button"
                        key={i.indice}
                        className={`indice-switch-btn${selectedVuelo.indice === i.indice ? ' indice-switch-btn--active' : ''}${i.estado === 'error' ? ' indice-switch-btn--error' : ''}`}
                        onClick={() => cambiarIndice(i.indice)}
                        title={i.estado !== 'completado' ? `Estado: ${i.estado}` : ''}
                      >
                        {INDICE_LABEL[i.indice] ?? i.indice}
                      </button>
                    ))}
                  </div>
                )}
                <div className="card-mapa-body">
                  {selectedVuelo
                    ? <AnalisisMap key={`${selectedVuelo.vueloId}-${selectedVuelo.indice}`} loteId={selectedVuelo.loteId} vueloId={selectedVuelo.vueloId} indice={selectedVuelo.indice} />
                    : (
                      <div className="mapa-placeholder">
                        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#c2c9b8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                          <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
                          <line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
                        </svg>
                        <p>Seleccioná un vuelo para ver su análisis</p>
                        <p className="empty-hint">Hacé clic en 🔍 en la tabla de arriba</p>
                      </div>
                    )
                  }
                </div>
              </div>
            </div>

            {/* Columna derecha */}
            <div className="dashboard-col-side">
              {/* Acciones Rápidas */}
              <div className="card">
                <div className="card-header">
                  <h2 className="card-title">⚡ Acciones Rápidas</h2>
                </div>
                <div className="card-body acciones-list">
                  <button className="accion-item accion-item--primary" onClick={() => setShowModalNuevoLote(true)}>
                    <div className="accion-icon">
                      <IconLotes />
                    </div>
                    <div className="accion-text">
                      <span className="accion-label">Nuevo Lote</span>
                      <span className="accion-sub">Registrá una nueva parcela</span>
                    </div>
                    <IconArrow />
                  </button>
                  <button className="accion-item" onClick={() => setShowModal(true)}>
                    <div className="accion-icon">
                      <IconCargar />
                    </div>
                    <div className="accion-text">
                      <span className="accion-label">Cargar Ortomosaico</span>
                      <span className="accion-sub">Subí imágenes multiespectral</span>
                    </div>
                    <IconArrow />
                  </button>
                  <button
                    className="accion-item"
                    disabled={!vueloRows.some(v => v.estado === 'completado')}
                    onClick={() => {
                      const ultimo = vueloRows.find(v => v.estado === 'completado')
                      if (ultimo) navigate(`/lotes/${ultimo.lote.id}/vuelos/${ultimo.vueloId}`)
                    }}
                  >
                    <div className="accion-icon">
                      <IconDiagnostico />
                    </div>
                    <div className="accion-text">
                      <span className="accion-label">Ver Diagnósticos</span>
                      <span className="accion-sub">
                        {vueloRows.some(v => v.estado === 'completado')
                          ? 'Resultados del último análisis'
                          : 'Cargá un ortomosaico primero'}
                      </span>
                    </div>
                    <IconArrow />
                  </button>
                  <button className="accion-item" disabled>
                    <div className="accion-icon">
                      <IconInformes />
                    </div>
                    <div className="accion-text">
                      <span className="accion-label">Generar Informe PDF</span>
                      <span className="accion-sub">Exportá resumen de campaña</span>
                    </div>
                    <IconArrow />
                  </button>
                </div>
              </div>

              {/* Actividad reciente */}
              <div className="card">
                <div className="card-header">
                  <h2 className="card-title">🔁 Actividad reciente</h2>
                </div>
                <div className="card-body">
                  <div className="actividad-feed">
                    {buildActivityFeed(loteRows, vueloRows, user?.nombre?.split(' ')[0] || 'el usuario').map((item, i) => (
                      <div key={i} className={`actividad-item actividad-item--${item.tipo}`}>
                        <span className="actividad-dot" />
                        <div className="actividad-content">
                          <p className="actividad-texto">{item.texto}</p>
                          <p className="actividad-tiempo">{fmtTiempoRelativo(item.fecha)}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
