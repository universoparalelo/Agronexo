import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { listarLotes, eliminarLote } from '../api/lotes'
import { CULTIVOS, cultivoMasReciente, etiquetaTipoCultivo } from '../utils/cultivos'
import SidebarNav from '../components/SidebarNav'
import TopbarPanel from '../components/TopbarPanel'
import ModalCargaGeoTIFF from '../components/ModalCargaGeoTIFF'
import ModalNuevoLote from '../components/ModalNuevoLote'
import ModalEditarLote from '../components/ModalEditarLote'
import { useAvisos } from '../components/AvisosProvider'
import ModalConfirmarEliminar from '../components/ModalConfirmarEliminar'
import ModalElegirLote from '../components/ModalElegirLote'
import { irAlUltimoDiagnostico } from '../utils/diagnosticos'

const ESTADO_LABELS = {
  pendiente:  'Pendiente',
  procesando: 'Procesando',
  completado: 'Completado',
  error:      'Error',
}

const PAGE_SIZE = 12


const IconCalendar = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
)
const IconPencil = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
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
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [showModalCarga, setShowModalCarga] = useState(false)
  const [showModalNuevoLote, setShowModalNuevoLote] = useState(false)
  const [showModalElegirLote, setShowModalElegirLote] = useState(false)
  const [loteParaEliminar, setLoteParaEliminar] = useState(null)
  const [loteParaEditar, setLoteParaEditar] = useState(null)
  const { avisar } = useAvisos()

  // Filtros de la grilla — búsqueda con debounce para no pegarle a la API en cada tecla.
  const [busqueda, setBusqueda] = useState('')
  const [q, setQ] = useState('')
  const [cultivoFiltro, setCultivoFiltro] = useState('')
  const [campanaFiltro, setCampanaFiltro] = useState('')
  const [estadoFiltro, setEstadoFiltro] = useState('')

  useEffect(() => {
    const t = setTimeout(() => { setQ(busqueda); setPage(1) }, 350)
    return () => clearTimeout(t)
  }, [busqueda])

  // Lista completa (sin filtros ni paginado) — la necesitan el modal de carga
  // de ortomosaico y el de "elegir lote", que tienen que poder ofrecer
  // cualquier lote del usuario, no solo los que entran en la página actual.
  const [lotesTodos, setLotesTodos] = useState([])
  const cargarLotesTodos = useCallback(async () => {
    try {
      const data = await listarLotes({ page_size: 100 })
      setLotesTodos(data.items ?? [])
    } catch {
      setLotesTodos([])
    }
  }, [])

  const cargarLotes = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listarLotes({
        page, page_size: PAGE_SIZE,
        q: q || undefined,
        cultivo: cultivoFiltro || undefined,
        campana: campanaFiltro || undefined,
        estado: estadoFiltro || undefined,
      })
      setLotes(data.items ?? [])
      setTotal(data.total ?? 0)
    } catch {
      setLotes([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [page, q, cultivoFiltro, campanaFiltro, estadoFiltro])

  useEffect(() => { cargarLotes() }, [cargarLotes])
  useEffect(() => { cargarLotesTodos() }, [cargarLotesTodos])

  function recargarTodo() {
    cargarLotes()
    cargarLotesTodos()
  }

  async function handleEliminar() {
    await eliminarLote(loteParaEliminar.id)
    setLoteParaEliminar(null)
    recargarTodo()
  }

  function handleVerDiagnosticos() {
    if (lotesTodos.length === 1) {
      irAlUltimoDiagnostico(navigate, lotesTodos[0].id)
      return
    }
    setShowModalElegirLote(true)
  }

  const totalPaginas = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="dashboard">
      {showModalCarga && (
        <ModalCargaGeoTIFF
          lotes={lotesTodos}
          onSuccess={() => { setShowModalCarga(false); recargarTodo() }}
          onLoteCreado={recargarTodo}
          onClose={() => setShowModalCarga(false)}
        />
      )}
      {showModalNuevoLote && (
        <ModalNuevoLote
          onSuccess={() => { setShowModalNuevoLote(false); recargarTodo() }}
          onClose={() => setShowModalNuevoLote(false)}
        />
      )}
      {loteParaEditar && (
        <ModalEditarLote
          lote={loteParaEditar}
          onSuccess={() => { setLoteParaEditar(null); recargarTodo(); avisar('Lote actualizado') }}
          onClose={() => setLoteParaEditar(null)}
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
          lotes={lotesTodos}
          onElegir={(loteId) => { setShowModalElegirLote(false); irAlUltimoDiagnostico(navigate, loteId) }}
          onClose={() => setShowModalElegirLote(false)}
        />
      )}

      <SidebarNav user={user} onVerDiagnosticos={handleVerDiagnosticos} plegable />

      <div className="dashboard-body">
        <TopbarPanel migas={[{ label: 'Lotes' }]} />

        <main className="dashboard-main">
          <div className="welcome-section lotes-encabezado">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div>
                <h1 className="welcome-title">Lotes registrados</h1>
              </div>
              <div style={{ display: 'flex', gap: '0.6rem' }}>
                <button className="btn-secondary" onClick={() => setShowModalNuevoLote(true)}>+ Nuevo Lote</button>
                <button className="btn-primary" onClick={() => setShowModalCarga(true)}>+ Cargar Ortomosaico</button>
              </div>
            </div>
          </div>

          <div className="lotes-filtros">
            <input
              type="text"
              className="lotes-filtro-input"
              placeholder="Buscar por nombre..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
            />
            <select
              className="lotes-filtro-select"
              value={cultivoFiltro}
              onChange={(e) => { setCultivoFiltro(e.target.value); setPage(1) }}
            >
              <option value="">Todos los cultivos</option>
              {CULTIVOS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <input
              type="number"
              className="lotes-filtro-input lotes-filtro-campana"
              placeholder="Campaña"
              value={campanaFiltro}
              onChange={(e) => { setCampanaFiltro(e.target.value); setPage(1) }}
            />
            <select
              className="lotes-filtro-select"
              value={estadoFiltro}
              onChange={(e) => { setEstadoFiltro(e.target.value); setPage(1) }}
            >
              <option value="">Cualquier estado</option>
              {Object.entries(ESTADO_LABELS).map(([valor, label]) => (
                <option key={valor} value={valor}>{label}</option>
              ))}
            </select>
          </div>

          {loading ? (
            <p className="estado-msg" style={{ padding: '1rem 0' }}>Cargando lotes...</p>
          ) : lotes.length === 0 ? (
            <div className="empty-state">
              {q || cultivoFiltro || campanaFiltro || estadoFiltro ? (
                <>
                  <p>Ningún lote coincide con esos filtros.</p>
                  <p className="empty-hint">Probá cambiarlos o limpiar la búsqueda.</p>
                </>
              ) : (
                <>
                  <p>No hay lotes registrados.</p>
                  <p className="empty-hint">Usá "+ Nuevo Lote" para crear el primero.</p>
                </>
              )}
            </div>
          ) : (
            <>
              <div className="lotes-grid">
                {lotes.map((lote) => {
                  const cultivo = etiquetaTipoCultivo(cultivoMasReciente(lote)?.tipo_cultivo)
                  return (
                    <div
                      className="lote-card lote-card--clicable"
                      key={lote.id}
                      role="link"
                      tabIndex={0}
                      onClick={() => navigate(`/lotes/${lote.id}`)}
                      onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/lotes/${lote.id}`) }}
                    >
                      <span className="lote-meta-icon lote-card-icono"><IconPlant /></span>
                      <div className="lote-card-body">
                        <div className="lote-card-title-row">
                          <div>
                            <h3 className="lote-card-nombre">
                              <span className="lote-card-nombre-link">{lote.nombre}</span>
                            </h3>
                            {cultivo && <span className="lote-crop-tag">{cultivo}</span>}
                          </div>
                          <div className="lote-card-acciones">
                            <button className="tbl-btn" title="Editar lote" onClick={(e) => { e.stopPropagation(); setLoteParaEditar(lote) }}>
                              <IconPencil />
                            </button>
                            <button className="tbl-btn tbl-btn--danger" title="Eliminar lote" onClick={(e) => { e.stopPropagation(); setLoteParaEliminar(lote) }}>
                              <IconTrash />
                            </button>
                          </div>
                        </div>

                        <div className="lote-card-meta">
                          {!cultivo && (
                            <div className="lote-meta-item" title="Cultivo: Sin cultivo">
                              <span className="lote-meta-icon"><IconPlant /></span>
                              <span className="lote-meta-val">Sin cultivo</span>
                            </div>
                          )}
                          <div className="lote-meta-item" title={`Superficie: ${lote.area_ha ? `${Math.round(lote.area_ha)} ha` : 'Sin límites'}`}>
                            <span className="lote-meta-icon"><IconArea /></span>
                            <span className="lote-meta-val">{lote.area_ha ? `${Math.round(lote.area_ha)} ha` : 'Sin límites'}</span>
                          </div>
                          <div className="lote-meta-item" title={`Último vuelo: ${lote.ultimo_vuelo_fecha ? fmtFecha(lote.ultimo_vuelo_fecha) : '—'}`}>
                            <span className="lote-meta-icon"><IconCalendarMini /></span>
                            <span className="lote-meta-val">{lote.ultimo_vuelo_fecha ? fmtFecha(lote.ultimo_vuelo_fecha) : '—'}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>

              {totalPaginas > 1 && (
                <div className="lotes-paginado">
                  <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                    ← Anterior
                  </button>
                  <span className="lotes-paginado-info">Página {page} de {totalPaginas} ({total} lotes)</span>
                  <button className="btn-secondary" disabled={page >= totalPaginas} onClick={() => setPage((p) => p + 1)}>
                    Siguiente →
                  </button>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  )
}
