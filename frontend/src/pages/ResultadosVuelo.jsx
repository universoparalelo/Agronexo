import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import client from '../api/client'
import { obtenerDiagnostico, obtenerZonas } from '../api/analisis'
import MapaZonas from '../components/MapaZonas'
import TablaDiagnostico from '../components/TablaDiagnostico'
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

  const [tab, setTab] = useState('zonas')
  const [diagnostico, setDiagnostico] = useState(null)
  const [diagnosticoLoading, setDiagnosticoLoading] = useState(false)
  const [diagnosticoError, setDiagnosticoError] = useState('')

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

  useEffect(() => {
    if (tab !== 'diagnostico' || diagnostico || diagnosticoLoading) return
    setDiagnosticoLoading(true)
    setDiagnosticoError('')
    obtenerDiagnostico(loteId, vueloId)
      .then(setDiagnostico)
      .catch(() => setDiagnosticoError('No se pudo generar el diagnóstico para este análisis.'))
      .finally(() => setDiagnosticoLoading(false))
  }, [tab, loteId, vueloId, diagnostico, diagnosticoLoading])

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
            {lote && (
              <span className={`cultivo-badge cultivo-${lote.cultivo}`}>
                {CULTIVO_LABELS[lote.cultivo] || lote.cultivo}
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
          <MapaZonas geojson={zonas} diagnostico={tab === 'diagnostico' ? diagnostico : null} />
        </div>

        <div className="resultados-sidebar">
          <div className="resultados-tabs">
            <button
              className={`resultados-tab ${tab === 'zonas' ? 'resultados-tab--activo' : ''}`}
              onClick={() => setTab('zonas')}
            >
              Zonas
            </button>
            <button
              className={`resultados-tab ${tab === 'diagnostico' ? 'resultados-tab--activo' : ''}`}
              onClick={() => setTab('diagnostico')}
            >
              Diagnóstico
            </button>
          </div>

          {tab === 'zonas' && (
            features.length > 0
              ? <>
                  <TablaZonas features={features} />
                  <button className="link-diagnostico" onClick={() => setTab('diagnostico')}>
                    Ver diagnóstico agronómico →
                  </button>
                </>
              : <p className="empty-hint">Sin zonas clasificadas para este análisis.</p>
          )}

          {tab === 'diagnostico' && (
            <>
              {diagnosticoLoading && (
                <div className="diagnostico-loading">
                  <span className="diagnostico-spinner" />
                  <p>Analizando zonas y generando diagnóstico agronómico...</p>
                </div>
              )}
              {diagnosticoError && <p className="empty-hint">{diagnosticoError}</p>}
              {diagnostico && <TablaDiagnostico diagnostico={diagnostico} />}
            </>
          )}
        </div>
      </main>
    </div>
  )
}
