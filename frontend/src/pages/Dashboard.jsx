import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useVueloProgreso } from '../hooks/useVueloProgreso'
import client from '../api/client'
import BarraProgreso from '../components/BarraProgreso'
import MapaIndice from '../components/MapaIndice'
import ModalCargaGeoTIFF from '../components/ModalCargaGeoTIFF'
import ModalLimites from '../components/ModalLimites'
import MiniMapaLote from '../components/MiniMapaLote'

const CULTIVO_LABEL = {
  soja: 'Soja',
  maiz: 'Maíz',
  algodon: 'Algodón',
  sorgo: 'Sorgo',
}

function AnalisisPanel({ loteId }) {
  const [vuelos, setVuelos] = useState([])
  const [loadingVuelos, setLoadingVuelos] = useState(true)

  useEffect(() => {
    setLoadingVuelos(true)
    client
      .get(`/lotes/${loteId}/vuelos`)
      .then(({ data }) => setVuelos(data))
      .catch(() => setVuelos([]))
      .finally(() => setLoadingVuelos(false))
  }, [loteId])

  const vuelo = vuelos[0] ?? null
  const { estado, geojson, errorMsg } = useVueloProgreso(
    vuelo ? loteId : null,
    vuelo?.vuelo_id ?? null,
  )

  if (loadingVuelos) return <p className="estado-msg">Cargando análisis...</p>

  if (!vuelo) {
    return (
      <div className="empty-state">
        <p>No hay vuelos procesados para este lote.</p>
        <p className="empty-hint">Subí un GeoTIFF para iniciar el análisis de índices.</p>
      </div>
    )
  }

  const estadoActual = estado?.estado ?? vuelo.estado

  if (estadoActual === 'completado' && geojson) {
    return <MapaIndice geojson={geojson} />
  }

  if (estadoActual === 'error' || errorMsg) {
    return (
      <div className="analisis-error">
        <p className="analisis-error-titulo">Error en el procesamiento</p>
        <p>{errorMsg ?? estado?.error ?? 'Ocurrió un error al procesar el vuelo.'}</p>
      </div>
    )
  }

  return (
    <BarraProgreso
      progreso={estado?.progreso ?? 0}
      mensaje={estado?.mensaje}
      estado={estadoActual}
    />
  )
}

export default function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [lotes, setLotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedLoteId, setSelectedLoteId] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [loteParaLimites, setLoteParaLimites] = useState(null)

  function cargarLotes() {
    setLoading(true)
    client
      .get('/lotes')
      .then(({ data }) => setLotes(data.items))
      .catch(() => setError('No se pudieron cargar los lotes.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargarLotes() }, [])

  function handleCargaExitosa(loteId) {
    setShowModal(false)
    cargarLotes()
    setSelectedLoteId(loteId)
  }

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const loteSeleccionado = lotes.find((l) => l.id === selectedLoteId)

  return (
    <div className="dashboard">
      {showModal && (
        <ModalCargaGeoTIFF
          onSuccess={handleCargaExitosa}
          onClose={() => setShowModal(false)}
        />
      )}
      {loteParaLimites && (
        <ModalLimites
          lote={loteParaLimites}
          onSuccess={() => { setLoteParaLimites(null); cargarLotes() }}
          onClose={() => setLoteParaLimites(null)}
        />
      )}
      <header className="dashboard-header">
        <div className="header-brand">
          <h1>AgroNexo</h1>
        </div>
        <div className="header-user">
          <span>{user?.nombre}</span>
          <button className="btn-logout" onClick={handleLogout}>
            Cerrar sesión
          </button>
        </div>
      </header>

      <main className="dashboard-main">
        <section className="lotes-section">
          <div className="section-title-row">
            <h2>Mis lotes</h2>
            <button className="btn-primary btn-sm" onClick={() => setShowModal(true)}>
              + Cargar GeoTIFF
            </button>
          </div>

          {loading && <p className="estado-msg">Cargando lotes...</p>}
          {error && <p className="error-message">{error}</p>}

          {!loading && !error && lotes.length === 0 && (
            <div className="empty-state">
              <p>Todavía no tenés lotes registrados.</p>
              <p className="empty-hint">Creá tu primer lote para comenzar el análisis.</p>
            </div>
          )}

          {!loading && lotes.length > 0 && (
            <div className="lotes-grid">
              {lotes.map((lote) => (
                <div
                  key={lote.id}
                  className={`lote-card${selectedLoteId === lote.id ? ' lote-card--activo' : ''}`}
                >
                  <div className="lote-card-header">
                    <h3>{lote.nombre}</h3>
                    <span className={`cultivo-badge cultivo-${lote.cultivo}`}>
                      {CULTIVO_LABEL[lote.cultivo] || lote.cultivo}
                    </span>
                  </div>
                  <MiniMapaLote geometry={lote.geometry} />
                  <div className="lote-card-body">
                    {lote.area_ha && (
                      <p className="lote-stat">
                        <strong>
                          {lote.area_ha.toLocaleString('es-AR', { maximumFractionDigits: 1 })}
                        </strong>{' '}
                        ha
                      </p>
                    )}
                    {lote.estadio_fenologico && (
                      <p className="lote-estadio">Estadio: {lote.estadio_fenologico}</p>
                    )}
                  </div>
                  <div className="lote-card-footer">
                    <button
                      className="btn-secondary btn-sm"
                      onClick={() => setSelectedLoteId(lote.id)}
                    >
                      Ver análisis
                    </button>
                    <button
                      className="btn-secondary btn-sm"
                      onClick={() => setLoteParaLimites(lote)}
                    >
                      Límites
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="mapa-section">
          <div className="section-title-row">
            <h2>
              {loteSeleccionado ? `Análisis — ${loteSeleccionado.nombre}` : 'Mapa'}
            </h2>
            {loteSeleccionado && (
              <button
                className="btn-secondary btn-sm"
                onClick={() => setSelectedLoteId(null)}
              >
                Cerrar
              </button>
            )}
          </div>

          {selectedLoteId ? (
            <AnalisisPanel key={selectedLoteId} loteId={selectedLoteId} />
          ) : (
            <div className="mapa-placeholder">
              <p>Seleccioná un lote para ver su análisis</p>
              <p className="empty-hint">
                NDVI, NDRE, SAVI y más índices de vegetación
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
