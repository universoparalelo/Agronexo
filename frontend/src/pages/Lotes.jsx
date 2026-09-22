import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { listarLotes, eliminarLote } from '../api/lotes'
import client from '../api/client'
import { cultivoMasReciente, etiquetaTipoCultivo } from '../utils/cultivos'
import SidebarNav from '../components/SidebarNav'
import TopbarPanel from '../components/TopbarPanel'
import ModalCargaGeoTIFF from '../components/ModalCargaGeoTIFF'
import ModalNuevoLote from '../components/ModalNuevoLote'
import ModalConfirmarEliminar from '../components/ModalConfirmarEliminar'
import ModalElegirLote from '../components/ModalElegirLote'


const IconCalendar = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
)
const IconZoom = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
)
const IconTrash = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
  </svg>
)
const IconPlant = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22v-9" />
    <path d="M9 8c2-3 5-4 8-4 0 4-2 7-5 8" />
    <path d="M12 13c-2-2-5-2-7 0 0 3 2 5 5 5" />
  </svg>
)
const IconArea = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
    <line x1="9" y1="3" x2="9" y2="18"/>
    <line x1="15" y1="6" x2="15" y2="21"/>
  </svg>
)
const IconFlight = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
  </svg>
)
const IconCalendarMini = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2"/>
    <line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/>
    <line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
)

function fmtFecha(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
  return `${d.getDate()} ${meses[d.getMonth()]} ${d.getFullYear()}`
}

export default function Lotes() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [lotes, setLotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModalCarga, setShowModalCarga] = useState(false)
  const [showModalNuevoLote, setShowModalNuevoLote] = useState(false)
  const [showModalElegirLote, setShowModalElegirLote] = useState(false)
  const [loteParaEliminar, setLoteParaEliminar] = useState(null)

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

  function handleVerDiagnosticos() {
    if (lotes.length === 1) {
      navigate(`/lotes/${lotes[0].id}`)
      return
    }
    setShowModalElegirLote(true)
  }

  return (
    <div className="dashboard">
      {showModalCarga && (
        <ModalCargaGeoTIFF
          lotes={lotes}
          onSuccess={() => { setShowModalCarga(false); cargarLotes() }}
          onLoteCreado={cargarLotes}
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
      {showModalElegirLote && (
        <ModalElegirLote
          lotes={lotes}
          onElegir={(loteId) => { setShowModalElegirLote(false); navigate(`/lotes/${loteId}`) }}
          onClose={() => setShowModalElegirLote(false)}
        />
      )}

      <SidebarNav user={user} onVerDiagnosticos={handleVerDiagnosticos} />

      <div className="dashboard-body">
        <TopbarPanel migas={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Lotes' }]} />

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
              {lotes.map((lote) => {
                const cultivo = etiquetaTipoCultivo(cultivoMasReciente(lote)?.tipo_cultivo)
                return (
                  <div className="lote-card" key={lote.id}>
                    <div className="lote-card-thumb">
                      <img src="/fondo.jpeg" alt={lote.nombre} />
                    </div>
                    <div className="lote-card-body">
                      <div className="lote-card-title-row">
                        <div>
                          <h3 className="lote-card-nombre">{lote.nombre}</h3>
                          {cultivo && <span className="lote-crop-tag">{cultivo}</span>}
                        </div>
                        <div className="lote-card-acciones">
                          <button className="tbl-btn" title="Ver detalle del lote" onClick={() => navigate(`/lotes/${lote.id}`)}>
                            <IconZoom />
                          </button>
                          <button className="tbl-btn tbl-btn--danger" title="Eliminar lote" onClick={() => setLoteParaEliminar(lote)}>
                            <IconTrash />
                          </button>
                        </div>
                      </div>

                      <div className="lote-card-meta">
                        <div className="lote-meta-item" title={`Cultivo: ${cultivo || 'Sin cultivo'}`}>
                          <span className="lote-meta-icon"><IconPlant /></span>
                          <span className="lote-meta-val">{cultivo || 'Sin cultivo'}</span>
                        </div>
                        <div className="lote-meta-item" title={`Superficie: ${lote.area_ha ? `${Math.round(lote.area_ha)} ha` : 'Sin límites'}`}>
                          <span className="lote-meta-icon"><IconArea /></span>
                          <span className="lote-meta-val">{lote.area_ha ? `${Math.round(lote.area_ha)} ha` : 'Sin límites'}</span>
                        </div>
                        <div className="lote-meta-item" title={`Misiones: ${lote.vuelos.length} vuelo${lote.vuelos.length !== 1 ? 's' : ''}`}>
                          <span className="lote-meta-icon"><IconFlight /></span>
                          <span className="lote-meta-val">{lote.vuelos.length} vuelo{lote.vuelos.length !== 1 ? 's' : ''}</span>
                        </div>
                        <div className="lote-meta-item" title={`Fecha de registro: ${fmtFecha(lote.created_at)}`}>
                          <span className="lote-meta-icon"><IconCalendarMini /></span>
                          <span className="lote-meta-val">{fmtFecha(lote.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
