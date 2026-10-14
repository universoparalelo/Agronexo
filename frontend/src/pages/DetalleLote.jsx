import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import client from '../api/client'
import { cultivoMasReciente, etiquetaTipoCultivo } from '../utils/cultivos'
import { fechaISOLocal, fechaDDMMAAAA } from '../utils/fechas'
import { listarVuelos, obtenerEstadoVuelo } from '../api/analisis'
import BotonVolver from '../components/BotonVolver'
import PanelLayout from '../components/PanelLayout'
import CalendarioMensual from '../components/CalendarioMensual'
import ModalCargaGeoTIFF from '../components/ModalCargaGeoTIFF'

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

function VueloCard({ vuelo, estadoActual, onVerResultados }) {
  const estadoStr = estadoActual.estado || vuelo.estado
  const progreso = estadoActual.progreso ?? null

  return (
    <div className="vuelo-card">
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
          <button className="btn-primary btn-sm" onClick={onVerResultados}>
            Ver resultados
          </button>
        )}
      </div>
    </div>
  )
}

export default function DetalleLote() {
  const { loteId } = useParams()
  const navigate = useNavigate()

  const [lote, setLote] = useState(null)
  const [vuelos, setVuelos] = useState([])
  const [estados, setEstados] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [vista, setVista] = useState('lista') // 'lista' | 'calendario'
  const [diaSeleccionado, setDiaSeleccionado] = useState(() => fechaISOLocal(new Date()))
  const [nuevoAnalisisAbierto, setNuevoAnalisisAbierto] = useState(false)

  const cargarLote = useCallback(() => {
    return Promise.all([
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

  useEffect(() => { cargarLote() }, [cargarLote])

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

  const vuelosDelDiaSeleccionado = vuelos
    .filter(v => fechaISOLocal(new Date(v.fecha_vuelo)) === diaSeleccionado)
    .sort((a, b) => new Date(b.fecha_vuelo) - new Date(a.fecha_vuelo))

  const contenido = (
    <>
      <div className="vuelos-header-row">
        <h2 className="vuelos-title">Vuelos registrados</h2>
        <div className="vuelos-vista-toggle">
          <button
            type="button"
            className={`vista-btn ${vista === 'lista' ? 'vista-btn--active' : ''}`}
            onClick={() => setVista('lista')}
            title="Vista lista"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="1" width="12" height="3" rx="0.5" fill="currentColor"/><rect x="1" y="5.5" width="12" height="3" rx="0.5" fill="currentColor" opacity="0.6"/><rect x="1" y="10" width="12" height="3" rx="0.5" fill="currentColor" opacity="0.35"/></svg>
          </button>
          <button
            type="button"
            className={`vista-btn ${vista === 'calendario' ? 'vista-btn--active' : ''}`}
            onClick={() => setVista('calendario')}
            title="Vista calendario"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="1" width="5.5" height="5.5" rx="1" fill="currentColor"/><rect x="7.5" y="1" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.6"/><rect x="1" y="7.5" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.6"/><rect x="7.5" y="7.5" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.35"/></svg>
          </button>
        </div>
      </div>

      {vuelos.length === 0 && (
        <div className="empty-state">
          <p>No hay vuelos registrados para este lote.</p>
          <p className="empty-hint">Usá "Cargar Ortomosaico" desde el Dashboard para subir un vuelo a este lote.</p>
        </div>
      )}

      {vuelos.length > 0 && vista === 'lista' && (
        <div className="vuelos-lista">
          {vuelos.map(vuelo => (
            <VueloCard
              key={vuelo.vuelo_id}
              vuelo={vuelo}
              estadoActual={estados[vuelo.vuelo_id] || vuelo}
              onVerResultados={() => navigate(`/lotes/${loteId}/vuelos/${vuelo.vuelo_id}`)}
            />
          ))}
        </div>
      )}

      {vuelos.length > 0 && vista === 'calendario' && (
        <div className="vuelos-calendario-inline">
          <div className="vuelos-calendario-inline-calendario">
            <CalendarioMensual
              vuelos={vuelos}
              vueloActualId={null}
              diaSeleccionado={diaSeleccionado}
              onSeleccionarDia={setDiaSeleccionado}
            />
          </div>

          <div className="vuelos-calendario-inline-lista">
            <div className="vuelos-calendario-inline-lista-header">
              <h3 className="vuelos-calendario-lista-titulo">Vuelos del {fechaDDMMAAAA(diaSeleccionado)}</h3>
              <button
                type="button"
                className="vuelos-calendario-nuevo-analisis"
                onClick={() => setNuevoAnalisisAbierto(true)}
              >
                ＋ Cargar nuevo análisis
              </button>
            </div>
            {vuelosDelDiaSeleccionado.length === 0 && (
              <p className="empty-hint">Sin vuelos cargados ese día.</p>
            )}
            <div className="vuelos-lista">
              {vuelosDelDiaSeleccionado.map(vuelo => (
                <VueloCard
                  key={vuelo.vuelo_id}
                  vuelo={vuelo}
                  estadoActual={estados[vuelo.vuelo_id] || vuelo}
                  onVerResultados={() => navigate(`/lotes/${loteId}/vuelos/${vuelo.vuelo_id}`)}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  )

  return (
    <PanelLayout
      migas={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Lotes', to: '/lotes' }, { label: lote.nombre }]}
      onVerDiagnosticos={() => navigate(`/lotes/${loteId}`)}
    >
      <main className={`detalle-main ${vista === 'calendario' ? 'detalle-main--calendario' : ''}`}>
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
          {lote.cultivos?.length > 0 && (
            <button
              type="button"
              className="btn-secondary pagina-encabezado-accion"
              onClick={() => navigate(`/lotes/${loteId}/ahorro`)}
            >
              Ahorro comparativo
            </button>
          )}
        </div>
        {contenido}
      </main>

      {nuevoAnalisisAbierto && (
        <ModalCargaGeoTIFF
          lotes={[lote]}
          loteIdInicial={loteId}
          loteFijo
          onSuccess={() => { setNuevoAnalisisAbierto(false); cargarLote() }}
          onClose={() => setNuevoAnalisisAbierto(false)}
        />
      )}
    </PanelLayout>
  )
}
