import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import client from '../api/client'

const CULTIVO_LABEL = {
  soja: 'Soja',
  maiz: 'Maíz',
  algodon: 'Algodón',
  sorgo: 'Sorgo',
}

export default function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [lotes, setLotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    client
      .get('/lotes')
      .then(({ data }) => setLotes(data.items))
      .catch(() => setError('No se pudieron cargar los lotes.'))
      .finally(() => setLoading(false))
  }, [])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="dashboard">
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
            <button className="btn-primary btn-sm" disabled>
              + Nuevo lote
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
                <div key={lote.id} className="lote-card">
                  <div className="lote-card-header">
                    <h3>{lote.nombre}</h3>
                    <span className={`cultivo-badge cultivo-${lote.cultivo}`}>
                      {CULTIVO_LABEL[lote.cultivo] || lote.cultivo}
                    </span>
                  </div>
                  <div className="lote-card-body">
                    {lote.area_ha && (
                      <p className="lote-stat">
                        <strong>{lote.area_ha.toLocaleString('es-AR', { maximumFractionDigits: 1 })}</strong> ha
                      </p>
                    )}
                    {lote.estadio_fenologico && (
                      <p className="lote-estadio">Estadio: {lote.estadio_fenologico}</p>
                    )}
                  </div>
                  <div className="lote-card-footer">
                    <button className="btn-secondary btn-sm" disabled>
                      Ver análisis
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="mapa-section">
          <div className="section-title-row">
            <h2>Mapa</h2>
          </div>
          <div className="mapa-placeholder">
            <p>El mapa con React-Leaflet se integra en el Sprint 4</p>
            <p className="empty-hint">aquí se mostrarán los lotes y los resultados de análisis NDVI</p>
          </div>
        </section>
      </main>
    </div>
  )
}
