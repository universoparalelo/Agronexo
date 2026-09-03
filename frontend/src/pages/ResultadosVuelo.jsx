import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import client from '../api/client'
import { obtenerZonas } from '../api/analisis'
import MapaZonas from '../components/MapaZonas'
import TablaZonas from '../components/TablaZonas'

const SENSOR_LABELS = {
  sentinel2:  'Sentinel-2',
  dji_mavic3: 'DJI Mavic 3',
}

const CULTIVO_LABELS = {
  soja: 'Soja', maiz: 'Maíz', algodon: 'Algodón', sorgo: 'Sorgo',
}

export default function ResultadosVuelo() {
  const { loteId, vueloId } = useParams()

  const [lote, setLote]   = useState(null)
  const [vuelo, setVuelo] = useState(null)
  const [zonas, setZonas] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  useEffect(() => {
    Promise.all([
      client.get(`/lotes/${loteId}`).then(r => r.data),
      client.get(`/lotes/${loteId}/vuelos`).then(r => r.data),
      obtenerZonas(loteId, vueloId),
    ])
      .then(([loteData, vuelosData, zonasData]) => {
        setLote(loteData)
        setVuelo(vuelosData.find(v => v.id === vueloId) || null)
        setZonas(zonasData)
      })
      .catch(() => setError('No se pudieron cargar los resultados del análisis.'))
      .finally(() => setLoading(false))
  }, [loteId, vueloId])

  if (loading) return <div className="page-loading">Cargando resultados...</div>

  if (error) return (
    <div className="page-error">
      <p>{error}</p>
      <Link to={`/lotes/${loteId}`} className="btn-back">← Vuelos</Link>
    </div>
  )

  const features = zonas?.features || []

  return (
    <div className="resultados-page">
      <header className="resultados-header">
        <div className="resultados-header-left">
          <Link to={`/lotes/${loteId}`} className="btn-back">← Vuelos</Link>
          <div className="resultados-titulo">
            <h1>{lote?.nombre}</h1>
            {lote?.cultivo_activo && (
              <span className={`cultivo-badge cultivo-${lote.cultivo_activo.cultivo}`}>
                {CULTIVO_LABELS[lote.cultivo_activo.cultivo] || lote.cultivo_activo.cultivo}
              </span>
            )}
          </div>
        </div>

        {vuelo && (
          <div className="resultados-meta">
            <span className="resultados-meta-item">{SENSOR_LABELS[vuelo.sensor] || vuelo.sensor}</span>
            <span className="resultados-meta-sep">·</span>
            <span className="resultados-meta-item">
              {new Date(vuelo.fecha_vuelo).toLocaleDateString('es-AR', {
                day: '2-digit', month: 'long', year: 'numeric',
              })}
            </span>
            {lote?.area_ha && (
              <>
                <span className="resultados-meta-sep">·</span>
                <span className="resultados-meta-item">
                  {lote.area_ha.toLocaleString('es-AR', { maximumFractionDigits: 1 })} ha
                </span>
              </>
            )}
          </div>
        )}
      </header>

      <main className="resultados-main">
        <div className="resultados-mapa">
          <MapaZonas geojson={zonas} />
        </div>

        <div className="resultados-sidebar">
          {features.length > 0
            ? <TablaZonas features={features} />
            : <p className="empty-hint">Sin zonas clasificadas para este análisis.</p>
          }
        </div>
      </main>
    </div>
  )
}
