import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { listarLotes, eliminarLote } from '../api/lotes'
import client from '../api/client'
import SidebarNav from '../components/SidebarNav'
import ModalCargaGeoTIFF from '../components/ModalCargaGeoTIFF'
import ModalNuevoLote from '../components/ModalNuevoLote'
import ModalConfirmarEliminar from '../components/ModalConfirmarEliminar'
import ModalCultivosLote from '../components/ModalCultivosLote'
import MiniMapaLote from '../components/MiniMapaLote'

const CULTIVO_LABEL = { soja: 'Soja', maiz: 'Maíz', algodon: 'Algodón', sorgo: 'Sorgo' }

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
const IconZoom = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
)
const IconTrash = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
  </svg>
)
const IconLeaf = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 20A7 7 0 019.8 6.1C15.5 5 17 3 17 3s3.5 2.5 3.5 8.5c0 4.5-3.5 8.5-9.5 8.5z"/>
    <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
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
function fmtFechaHoy() {
  return new Date().toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

export default function Lotes() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [lotes, setLotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModalCarga, setShowModalCarga] = useState(false)
  const [showModalNuevoLote, setShowModalNuevoLote] = useState(false)
  const [loteParaEliminar, setLoteParaEliminar] = useState(null)
  const [mapaExpandidoId, setMapaExpandidoId] = useState(null)
  const [loteCultivos, setLoteCultivos] = useState(null)

  useEffect(() => {
    if (!mapaExpandidoId) return
    function onKeyDown(e) {
      if (e.key === 'Escape') setMapaExpandidoId(null)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [mapaExpandidoId])

  const cargarLotes = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listarLotes()
      const items = data.items ?? []
      const results = await Promise.allSettled(
        items.map(l => client.get(`/lotes/${l.id}/vuelos`))
      )
      setLotes(items.map((l, i) => ({
        ...l,
        vuelos: results[i].status === 'fulfilled' ? (results[i].value.data ?? []) : [],
      })))
    } catch {
      setLotes([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { cargarLotes() }, [cargarLotes])

  async function handleEliminar() {
    await eliminarLote(loteParaEliminar.id)
    setLoteParaEliminar(null)
    cargarLotes()
  }

  return (
    <div className="dashboard">
      {showModalCarga && (
        <ModalCargaGeoTIFF
          lotes={lotes}
          onSuccess={() => { setShowModalCarga(false); cargarLotes() }}
          onClose={() => setShowModalCarga(false)}
        />
      )}
      {showModalNuevoLote && (
        <ModalNuevoLote
          onSuccess={() => { setShowModalNuevoLote(false); cargarLotes() }}
          onClose={() => setShowModalNuevoLote(false)}
        />
      )}
      {loteParaEliminar && (
        <ModalConfirmarEliminar
          titulo="Eliminar lote"
          mensaje={`¿Seguro que querés eliminar el lote "${loteParaEliminar.nombre}"? Esta acción no se puede deshacer.`}
          onConfirmar={handleEliminar}
          onClose={() => setLoteParaEliminar(null)}
        />
      )}
      {loteCultivos && (
        <ModalCultivosLote
          lote={loteCultivos}
          onClose={() => setLoteCultivos(null)}
        />
      )}

      <SidebarNav user={user} onCargarOrtomosaico={() => setShowModalCarga(true)} />

      <div className="dashboard-body">
        <header className="topbar">
          <nav className="topbar-breadcrumb">
            <span>Dashboard</span>
            <span className="breadcrumb-sep">›</span>
            <span className="breadcrumb-active">Lotes</span>
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
          <div className="welcome-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div>
                <h1 className="welcome-title">Lotes registrados</h1>
                <p className="welcome-sub">Todas tus parcelas — creá una nueva o eliminá las que ya no uses.</p>
              </div>
              <div style={{ display: 'flex', gap: '0.6rem' }}>
                <button className="btn-secondary" onClick={() => setShowModalNuevoLote(true)}>+ Nuevo Lote</button>
                <button className="btn-primary" onClick={() => setShowModalCarga(true)}>Cargar Ortomosaico</button>
              </div>
            </div>
          </div>

          {loading ? (
            <p className="estado-msg" style={{ padding: '1rem 0' }}>Cargando lotes...</p>
          ) : lotes.length === 0 ? (
            <div className="empty-state">
              <p>No hay lotes registrados.</p>
              <p className="empty-hint">Usá "+ Nuevo Lote" para crear el primero.</p>
            </div>
          ) : (
            <div className="lotes-grid">
              {lotes.map((lote) => (
                <div className="lote-card" key={lote.id}>
                  <MiniMapaLote geometry={lote.geometry} />
                  {lote.geometry && (
                    <button
                      className="mini-mapa-expand-btn"
                      title="Expandir mapa"
                      onClick={() => setMapaExpandidoId(lote.id)}
                    >
                      <IconExpandir />
                    </button>
                  )}
                  {mapaExpandidoId === lote.id && (
                    <>
                      <div className="mapa-expand-backdrop" onClick={() => setMapaExpandidoId(null)} />
                      <div className="lote-mapa-overlay">
                        <div className="lote-mapa-overlay-header">
                          <h3>{lote.nombre}</h3>
                          <button className="modal-close" onClick={() => setMapaExpandidoId(null)} aria-label="Cerrar">✕</button>
                        </div>
                        <div className="lote-mapa-overlay-body">
                          <MiniMapaLote geometry={lote.geometry} expandido />
                        </div>
                      </div>
                    </>
                  )}
                  <div className="lote-card-body">
                    <div className="lote-card-title-row">
                      <h3>{lote.nombre}</h3>
                      <div className="lote-card-acciones">
                        <button className="tbl-btn" title="Ver cultivos" onClick={() => setLoteCultivos(lote)}>
                          <IconLeaf />
                        </button>
                        <button className="tbl-btn" title="Ver detalle" onClick={() => navigate(`/lotes/${lote.id}`)}>
                          <IconZoom />
                        </button>
                        <button className="tbl-btn tbl-btn--danger" title="Eliminar lote" onClick={() => setLoteParaEliminar(lote)}>
                          <IconTrash />
                        </button>
                      </div>
                    </div>
                    <div className="lote-card-meta">
                      <span>🌱 {lote.cultivo_activo ? (CULTIVO_LABEL[lote.cultivo_activo.cultivo] ?? lote.cultivo_activo.cultivo) : 'Sin cultivo activo'}</span>
                      <span>📐 {lote.area_ha ? `${Math.round(lote.area_ha)} ha` : 'Sin límites'}</span>
                      <span>🛰️ {lote.vuelos.length} vuelo{lote.vuelos.length !== 1 ? 's' : ''}</span>
                      <span>🪨 {lote.suelo?.tipo ?? 'Sin suelo'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
