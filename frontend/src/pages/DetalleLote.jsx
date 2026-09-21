import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import client from '../api/client'
import { cultivoMasReciente, etiquetaTipoCultivo } from '../utils/cultivos'
import { listarVuelos, obtenerEstadoVuelo } from '../api/analisis'
import BotonVolver from '../components/BotonVolver'
import PanelLayout from '../components/PanelLayout'

const ESTADO_LABELS = {
  pendiente:  'Pendiente',
  procesando: 'Procesando',
  completado: 'Completado',
  error:      'Error',
}

const SENSOR_LABELS = {
  sentinel2:  'Sentinel-2',
  dji_mavic3: 'DJI Mavic 3',
}

export default function DetalleLote() {
  const { loteId } = useParams()
  const navigate = useNavigate()

  const [lote, setLote] = useState(null)
  const [vuelos, setVuelos] = useState([])
  const [estados, setEstados] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      client.get(`/lotes/${loteId}`).then(r => r.data),
      listarVuelos(loteId),
    ])
      .then(([loteData, vuelosData]) => {
        setLote(loteData)
        setVuelos(vuelosData)
      })
      .catch(() => setError('No se pudo cargar la información del lote.'))
      .finally(() => setLoading(false))
  }, [loteId])

  const actualizarEstados = useCallback(async () => {
    const activos = vuelos.filter(v => v.estado === 'pendiente' || v.estado === 'procesando')
    if (!activos.length) return

    const resultados = await Promise.allSettled(
      activos.map(v => obtenerEstadoVuelo(loteId, v.vuelo_id))
    )

    const nuevos = {}
    activos.forEach((v, i) => {
      if (resultados[i].status === 'fulfilled') nuevos[v.vuelo_id] = resultados[i].value
    })
    setEstados(prev => ({ ...prev, ...nuevos }))

    const terminaron = resultados.some(
      r => r.status === 'fulfilled' &&
        (r.value.estado === 'completado' || r.value.estado === 'error')
    )
    if (terminaron) listarVuelos(loteId).then(setVuelos)
  }, [vuelos, loteId])

  useEffect(() => {
    const hayActivos = vuelos.some(v => v.estado === 'pendiente' || v.estado === 'procesando')
    if (!hayActivos) return
    const id = setInterval(actualizarEstados, 3000)
    return () => clearInterval(id)
  }, [vuelos, actualizarEstados])

  if (loading) return <div className="page-loading">Cargando lote...</div>
  if (error) return (
    <div className="page-error">
      <p>{error}</p>
      <BotonVolver to="/dashboard" claro>Volver a mis lotes</BotonVolver>
    </div>
  )

  const contenido = (
    <>
      <h2 className="vuelos-title">Vuelos registrados</h2>

      {vuelos.length === 0 && (
        <div className="empty-state">
          <p>No hay vuelos registrados para este lote.</p>
          <p className="empty-hint">Usá "Cargar Ortomosaico" desde el Dashboard para subir un vuelo a este lote.</p>
        </div>
      )}

      <div className="vuelos-lista">
        {vuelos.map(vuelo => {
          const estadoActual = estados[vuelo.vuelo_id] || vuelo
          const estadoStr = estadoActual.estado || vuelo.estado
          const progreso = estadoActual.progreso ?? null

          return (
            <div key={vuelo.vuelo_id} className="vuelo-card">
              <div className="vuelo-card-info">
                <p className="vuelo-fecha">
                  {new Date(vuelo.fecha_vuelo).toLocaleDateString('es-AR', {
                    day: '2-digit', month: 'long', year: 'numeric',
                  })}
                </p>
                <p className="vuelo-sensor">{SENSOR_LABELS[vuelo.sensor] || vuelo.sensor}</p>
                {vuelo.estadio_fenologico && (
                  <span className="vuelo-estadio-tag">{vuelo.estadio_fenologico}</span>
                )}
              </div>

              <div className="vuelo-card-estado">
                <span className={`estado-badge estado-${estadoStr}`}>
                  {estadoStr === 'procesando' && <span className="estado-spinner" />}
                  {ESTADO_LABELS[estadoStr] || estadoStr}
                </span>

                {(estadoStr === 'procesando' || estadoStr === 'pendiente') && progreso != null && (
                  <div className="progreso-bar-wrapper">
                    <div className="progreso-bar" style={{ width: `${progreso}%` }} />
                    <span className="progreso-pct">{progreso}%</span>
                  </div>
                )}

                {estadoActual.mensaje && estadoStr === 'procesando' && (
                  <p className="vuelo-mensaje">{estadoActual.mensaje}</p>
                )}

                {estadoStr === 'error' && (estadoActual.error || vuelo.error_detalle) && (
                  <p className="vuelo-error">{estadoActual.error || vuelo.error_detalle}</p>
                )}
              </div>

              <div className="vuelo-card-acciones">
                {vuelo.estado === 'completado' && (
                  <button
                    className="btn-primary btn-sm"
                    onClick={() => navigate(`/lotes/${loteId}/vuelos/${vuelo.vuelo_id}`)}
                  >
                    Ver resultados
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </>
  )

  return (
    <PanelLayout
      migas={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Lotes', to: '/lotes' }, { label: lote.nombre }]}
      onVerDiagnosticos={() => navigate(`/lotes/${loteId}`)}
    >
      <main className="detalle-main">
        <div className="pagina-encabezado">
          <h1>{lote.nombre}</h1>
          {cultivoMasReciente(lote) && (
            <span className={`cultivo-badge cultivo-${cultivoMasReciente(lote).tipo_cultivo}`}>
              {etiquetaTipoCultivo(cultivoMasReciente(lote).tipo_cultivo)}
            </span>
          )}
          {lote.area_ha && (
            <span className="pagina-encabezado-meta">
              {lote.area_ha.toLocaleString('es-AR', { maximumFractionDigits: 1 })} ha
            </span>
          )}
        </div>
        {contenido}
      </main>
    </PanelLayout>
  )
}
