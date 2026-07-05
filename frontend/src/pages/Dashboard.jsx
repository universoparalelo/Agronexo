import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useVueloProgreso } from '../hooks/useVueloProgreso'
import client from '../api/client'
import BarraProgreso from '../components/BarraProgreso'
import MapaIndice from '../components/MapaIndice'
import ModalCargaGeoTIFF from '../components/ModalCargaGeoTIFF'
import ModalLimites from '../components/ModalLimites'

/* ──────── Icons ──────── */
const IconDashboard = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
    <rect x="3" y="3" width="7" height="7" rx="1.5"/>
    <rect x="14" y="3" width="7" height="7" rx="1.5"/>
    <rect x="3" y="14" width="7" height="7" rx="1.5"/>
    <rect x="14" y="14" width="7" height="7" rx="1.5"/>
  </svg>
)
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
    <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
    <path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
  </svg>
)
const IconPlus = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
)

/* ──────── Helpers ──────── */
const CULTIVO_LABEL = { soja: 'Soja', maiz: 'Maíz', algodon: 'Algodón', sorgo: 'Sorgo' }

const ESTADO_BADGE = {
  completado: { label: 'Óptimo',     cls: 'badge-optimo' },
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

/* ──────── Sidebar ──────── */
function SidebarNav({ activeSection, onSection, user }) {
  const sections = [
    {
      label: 'PRINCIPAL',
      items: [
        { id: 'dashboard',   icon: <IconDashboard />, label: 'Dashboard' },
        { id: 'lotes',       icon: <IconLotes />,     label: 'Lotes' },
        { id: 'cargar',      icon: <IconCargar />,    label: 'Cargar Ortomosaico' },
      ],
    },
    {
      label: 'RESULTADOS',
      items: [
        { id: 'diagnostico', icon: <IconDiagnostico />, label: 'Diagnósticos', badge: 2 },
        { id: 'informes',    icon: <IconInformes />,    label: 'Informes' },
      ],
    },
    {
      label: 'SISTEMA',
      items: [
        { id: 'config', icon: <IconConfig />, label: 'Configuración' },
      ],
    },
  ]

  const initials = user?.nombre
    ? user.nombre.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'U'

  return (
    <aside className="sidebar-nav">
      <div className="sidebar-logo-wrap">
        <div className="sidebar-logo-mark" />
        <div>
          <span className="sidebar-logo-text">AgroNexo</span>
          <span className="sidebar-beta">BETA</span>
        </div>
      </div>

      <nav className="sidebar-menu">
        {sections.map(({ label, items }) => (
          <div key={label} className="sidebar-section">
            <span className="sidebar-section-label">{label}</span>
            {items.map(({ id, icon, label: itemLabel, badge }) => (
              <button
                key={id}
                className={`sidebar-link${activeSection === id ? ' sidebar-link--active' : ''}`}
                onClick={() => onSection(id)}
                title={itemLabel}
              >
                <span className="sidebar-link-icon">{icon}</span>
                <span className="sidebar-link-label">{itemLabel}</span>
                {badge && <span className="sidebar-badge">{badge}</span>}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-user">
        <div className="sidebar-user-avatar">{initials}</div>
        <div className="sidebar-user-info">
          <span className="sidebar-user-name">{user?.nombre ?? 'Usuario'}</span>
          <span className="sidebar-user-role">Productor Agri</span>
        </div>
      </div>
    </aside>
  )
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
function AnalisisMap({ loteId }) {
  const [vuelos, setVuelos] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    client.get(`/lotes/${loteId}/vuelos`)
      .then(({ data }) => setVuelos(data))
      .catch(() => setVuelos([]))
      .finally(() => setLoading(false))
  }, [loteId])

  const vuelo = vuelos[0] ?? null
  const { estado, geojson, errorMsg } = useVueloProgreso(
    vuelo ? loteId : null,
    vuelo?.vuelo_id ?? vuelo?.id ?? null,
  )

  if (loading) return <p className="estado-msg" style={{ padding: '1rem' }}>Cargando análisis...</p>
  if (!vuelo)  return <p className="estado-msg" style={{ padding: '1rem' }}>Sin análisis para este lote.</p>

  const estadoActual = estado?.estado ?? vuelo.estado
  if (estadoActual === 'completado' && geojson) return <MapaIndice geojson={geojson} />
  if (estadoActual === 'error' || errorMsg) {
    return <p className="estado-msg" style={{ padding: '1rem', color: '#b91c1c' }}>Error en el procesamiento.</p>
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
  const [loteParaLimites, setLoteParaLimites] = useState(null)
  const [activeSection, setActiveSection] = useState('dashboard')
  const [selectedLoteId, setSelectedLoteId] = useState(null)
  const [page, setPage] = useState(1)
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const PAGE_SIZE = 4

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

  function handleCargaExitosa(loteId) {
    setShowModal(false)
    cargarDatos()
    setSelectedLoteId(loteId)
  }

  async function handleEliminar(loteId) {
    setDeleting(true)
    try {
      await client.delete(`/lotes/${loteId}`)
      if (selectedLoteId === loteId) setSelectedLoteId(null)
      setConfirmDeleteId(null)
      cargarDatos()
    } catch {
      // error silencioso — el lote seguirá en la lista
    } finally {
      setDeleting(false)
    }
  }

  const totalAnalisis = loteRows.reduce((acc, l) => acc + l.vuelos.length, 0)
  const totalPages    = Math.max(1, Math.ceil(loteRows.length / PAGE_SIZE))
  const pageRows      = loteRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const selectedLote  = loteRows.find(l => l.id === selectedLoteId)

  return (
    <div className="dashboard">
      {showModal && (
        <ModalCargaGeoTIFF onSuccess={handleCargaExitosa} onClose={() => setShowModal(false)} />
      )}
      {loteParaLimites && (
        <ModalLimites
          lote={loteParaLimites}
          onSuccess={() => { setLoteParaLimites(null); cargarDatos() }}
          onClose={() => setLoteParaLimites(null)}
        />
      )}

      {confirmDeleteId && (
        <div className="modal-overlay">
          <div className="modal-box" style={{ maxWidth: 380 }}>
            <div className="modal-header">
              <h2>Eliminar lote</h2>
              <button className="modal-close" onClick={() => setConfirmDeleteId(null)}>×</button>
            </div>
            <div className="card-body" style={{ padding: '1.25rem 2rem 1.5rem' }}>
              <p style={{ color: '#374151', marginBottom: '1.25rem' }}>
                ¿Estás seguro? Esta acción no se puede deshacer. El lote y todos sus vuelos serán eliminados.
              </p>
              <div className="modal-actions">
                <button className="btn-secondary" onClick={() => setConfirmDeleteId(null)}>
                  Cancelar
                </button>
                <button
                  className="btn-primary"
                  style={{ background: '#b91c1c' }}
                  disabled={deleting}
                  onClick={() => handleEliminar(confirmDeleteId)}
                >
                  {deleting ? 'Eliminando...' : 'Eliminar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <SidebarNav activeSection={activeSection} onSection={setActiveSection} user={user} />

      <div className="dashboard-body">
        {/* Topbar */}
        <header className="topbar">
          <nav className="topbar-breadcrumb">
            <span>Dashboard</span>
            <span className="breadcrumb-sep">›</span>
            <span className="breadcrumb-active">Resumen</span>
          </nav>
          <div className="topbar-actions">
            <button className="btn-primary btn-sm" onClick={() => setShowModal(true)}>
              <IconPlus /> Nuevo análisis
            </button>
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
              delta={loteRows.length > 0 ? `${loteRows.length} registrados` : null}
              deltaType="up"
              icon={<IconLotes />}
            />
            <KpiCard
              label="ANÁLISIS REALIZADOS"
              value={totalAnalisis || '—'}
              delta={totalAnalisis > 0 ? `+${totalAnalisis} procesados` : null}
              deltaType="up"
              icon={<IconDiagnostico />}
            />
            <KpiCard
              label="RECOMENDACIONES ACTIVAS"
              value="—"
              delta="Próximamente"
              deltaType="neutral"
              icon={<IconInformes />}
            />
            <KpiCard
              label="AHORRO ESTIMADO"
              value="—"
              delta="Motor de diagnóstico pendiente"
              deltaType="neutral"
              icon={<IconConfig />}
              highlight
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
                <div className="card-body" style={{ padding: '0' }}>
                  {loading ? (
                    <p className="estado-msg" style={{ padding: '1rem 1.1rem' }}>Cargando...</p>
                  ) : loteRows.length === 0 ? (
                    <div className="empty-state">
                      <p>No hay lotes registrados.</p>
                      <p className="empty-hint">Subí un GeoTIFF para comenzar el análisis.</p>
                    </div>
                  ) : (
                    <>
                      <table className="analisis-table">
                        <thead>
                          <tr>
                            <th>LOTE / CULTIVO</th>
                            <th>FECHA</th>
                            <th>ÍNDICE NDVI</th>
                            <th>ESTADO</th>
                            <th>ACCIÓN</th>
                          </tr>
                        </thead>
                        <tbody>
                          {pageRows.map(lote => {
                            const vuelo = lote.vuelos[0]
                            const badge = vuelo
                              ? (ESTADO_BADGE[vuelo.estado] ?? { label: vuelo.estado, cls: 'badge-procesando' })
                              : null
                            return (
                              <tr key={lote.id} className={selectedLoteId === lote.id ? 'tr--active' : ''}>
                                <td>
                                  <div className="td-lote-nombre">{lote.nombre}</div>
                                  <div className="td-lote-info">
                                    {CULTIVO_LABEL[lote.cultivo] ?? lote.cultivo}
                                    {lote.area_ha ? ` · ${Math.round(lote.area_ha)} ha` : ''}
                                    {' · Chaco'}
                                  </div>
                                </td>
                                <td className="td-fecha">{vuelo ? fmtFecha(vuelo.created_at) : '—'}</td>
                                <td className="td-ndvi">—</td>
                                <td>
                                  {badge
                                    ? <span className={`table-badge ${badge.cls}`}>{badge.label}</span>
                                    : <span className="table-badge badge-none">Sin análisis</span>
                                  }
                                </td>
                                <td>
                                  <div className="td-acciones">
                                    <button
                                      className="tbl-btn"
                                      title="Ver análisis"
                                      onClick={() => setSelectedLoteId(lote.id)}
                                    >
                                      <IconZoom />
                                    </button>
                                    <button
                                      className="tbl-btn"
                                      title="Límites"
                                      onClick={() => setLoteParaLimites(lote)}
                                    >
                                      <IconMap />
                                    </button>
                                    <button
                                      className="tbl-btn tbl-btn--danger"
                                      title="Eliminar lote"
                                      onClick={() => setConfirmDeleteId(lote.id)}
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
                        <span>Mostrando {pageRows.length} de {loteRows.length} lotes</span>
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
              <div className="card card--mapa">
                <div className="card-header">
                  <div>
                    <h2 className="card-title">📍 Vista geoespacial</h2>
                    <p className="card-sub">
                      {selectedLote
                        ? `Análisis — ${selectedLote.nombre}`
                        : 'Mapa de lotes registrados en la zona norte'}
                    </p>
                  </div>
                  {selectedLote && (
                    <button className="card-link" onClick={() => setSelectedLoteId(null)}>
                      Cerrar ×
                    </button>
                  )}
                </div>
                <div className="card-mapa-body">
                  {selectedLoteId
                    ? <AnalisisMap key={selectedLoteId} loteId={selectedLoteId} />
                    : (
                      <div className="mapa-placeholder">
                        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#c2c9b8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                          <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
                          <line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
                        </svg>
                        <p>Seleccioná un lote para ver su análisis</p>
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
                  <button className="accion-item accion-item--primary" onClick={() => setShowModal(true)}>
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
                  <button className="accion-item" disabled>
                    <div className="accion-icon">
                      <IconDiagnostico />
                    </div>
                    <div className="accion-text">
                      <span className="accion-label">Ver Diagnósticos</span>
                      <span className="accion-sub">Motor de diagnóstico pendiente</span>
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
                    {[
                      { tipo: 'ok',     texto: 'Análisis completado en Lote Norte #1',           tiempo: 'Hace 2 horas' },
                      { tipo: 'upload', texto: 'Nuevo ortomosaico cargado para Lote Este #7',    tiempo: 'Hace 6 horas' },
                      { tipo: 'alerta', texto: 'Alerta detectada: Estrés hídrico en Lote Central #5', tiempo: 'Ayer a las 18:45' },
                      { tipo: 'user',   texto: 'Perfil actualizado por Juan García',             tiempo: 'Ayer a las 09:20' },
                    ].map((item, i) => (
                      <div key={i} className={`actividad-item actividad-item--${item.tipo}`}>
                        <span className="actividad-dot" />
                        <div className="actividad-content">
                          <p className="actividad-texto">{item.texto}</p>
                          <p className="actividad-tiempo">{item.tiempo}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  <button className="card-link card-link--center">Ver historial completo</button>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
