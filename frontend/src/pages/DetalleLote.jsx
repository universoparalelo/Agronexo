import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import client from '../api/client'
import { cultivoMasReciente, etiquetaTipoCultivo } from '../utils/cultivos'
import { fechaISOLocal, fechaDDMMAAAA } from '../utils/fechas'
import { eliminarVuelo, listarVuelos, obtenerEstadoVuelo } from '../api/analisis'
import BotonVolver from '../components/BotonVolver'
import PanelLayout from '../components/PanelLayout'
import CalendarioMensual from '../components/CalendarioMensual'
import ModalCargaGeoTIFF from '../components/ModalCargaGeoTIFF'
import ModalEditarLote from '../components/ModalEditarLote'
import ModalEditarVuelo from '../components/ModalEditarVuelo'
import { useAvisos } from '../components/AvisosProvider'
import ModalConfirmarEliminar from '../components/ModalConfirmarEliminar'
import { TIPOS_SUELO } from '../utils/suelos'

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

function EstadoVuelo({ vuelo, estadoStr }) {
  const n = vuelo.zonas_atencion
  if (estadoStr === 'completado' && n != null) {
    return n > 0
      ? <span className="estado-badge estado-atencion">{n} zona{n === 1 ? '' : 's'} requiere{n === 1 ? '' : 'n'} atención</span>
      : <span className="estado-badge estado-completado">Sin problemas</span>
  }
  return (
    <span className={`estado-badge estado-${estadoStr}`}>
      {estadoStr === 'procesando' && <span className="estado-spinner" />}
      {ESTADO_LABELS[estadoStr] || estadoStr}
    </span>
  )
}

function VueloCard({ vuelo, estadoActual, onVerResultados, onEditar, onEliminar }) {
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
        <EstadoVuelo vuelo={vuelo} estadoStr={estadoStr} />

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
        <button type="button" className="tbl-btn" title="Editar vuelo" aria-label="Editar vuelo" onClick={onEditar}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
          </svg>
        </button>
        <button type="button" className="tbl-btn tbl-btn--danger" title="Eliminar vuelo" aria-label="Eliminar vuelo" onClick={onEliminar}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
          </svg>
        </button>
      </div>
    </div>
  )
}

function VueloFila({ vuelo, estadoActual, onVerResultados, onEditar, onEliminar }) {
  const estadoStr = estadoActual.estado || vuelo.estado
  const progreso = estadoActual.progreso ?? null

  return (
    <tr>
      <td className="tabla-vuelos-fecha">
        {new Date(vuelo.fecha_vuelo).toLocaleDateString('es-AR', { day: '2-digit', month: 'long', year: 'numeric' })}
      </td>
      <td>{SENSOR_LABELS[vuelo.sensor] || vuelo.sensor}</td>
      <td>{vuelo.estadio_fenologico ? <span className="vuelo-estadio-tag">{vuelo.estadio_fenologico}</span> : '—'}</td>
      <td>
        <EstadoVuelo vuelo={vuelo} estadoStr={estadoStr} />
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
      </td>
      <td className="tabla-vuelos-acciones">
        <div>
          {vuelo.estado === 'completado' && (
            <button className="btn-primary btn-sm" onClick={onVerResultados}>
              Ver resultados
            </button>
          )}
          <button type="button" className="tbl-btn" title="Editar vuelo" aria-label="Editar vuelo" onClick={onEditar}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
          </button>
          <button type="button" className="tbl-btn tbl-btn--danger" title="Eliminar vuelo" aria-label="Eliminar vuelo" onClick={onEliminar}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </button>
        </div>
      </td>
    </tr>
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
  const [editandoLote, setEditandoLote] = useState(false)
  const [vueloParaEditar, setVueloParaEditar] = useState(null)
  const { avisar } = useAvisos()
  const [vueloParaEliminar, setVueloParaEliminar] = useState(null)

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

  async function handleEliminarVuelo() {
    await eliminarVuelo(loteId, vueloParaEliminar.vuelo_id)
    setVueloParaEliminar(null)
    cargarLote()
  }

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
    <section className="vuelos-tarjeta">
      <div className="vuelos-toolbar">
        <div>
          <h2 className="vuelos-title">Vuelos registrados</h2>
          <span className="vuelos-conteo">
            {vuelos.length} vuelo{vuelos.length === 1 ? '' : 's'} registrado{vuelos.length === 1 ? '' : 's'}
          </span>
        </div>
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
          <p className="empty-hint">Usá "Cargar ortomosaico" para subir un vuelo a este lote.</p>
        </div>
      )}

      {vuelos.length > 0 && vista === 'lista' && (
        <table className="tabla-vuelos">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Sensor</th>
              <th>Estadio</th>
              <th>Estado</th>
              <th className="tabla-vuelos-acciones">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {vuelos.map(vuelo => (
              <VueloFila
                key={vuelo.vuelo_id}
                vuelo={vuelo}
                estadoActual={estados[vuelo.vuelo_id] || vuelo}
                onVerResultados={() => navigate(`/lotes/${loteId}/vuelos/${vuelo.vuelo_id}`)}
                onEditar={() => setVueloParaEditar(vuelo)}
                onEliminar={() => setVueloParaEliminar(vuelo)}
              />
            ))}
          </tbody>
        </table>
      )}

      {vuelos.length > 0 && vista === 'calendario' && (
        <div className="vuelos-tarjeta-cuerpo">
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
                  onEditar={() => setVueloParaEditar(vuelo)}
                  onEliminar={() => setVueloParaEliminar(vuelo)}
                />
              ))}
            </div>
          </div>
        </div>
        </div>
      )}
    </section>
  )

  const ultimoVuelo = vuelos.length > 0 ? new Date(vuelos[0].fecha_vuelo).toLocaleDateString('es-AR') : null
  const suelo = TIPOS_SUELO.find((t) => t.value && t.value === lote.tipo_suelo)?.label

  const cabecera = (
    <div className="detalle-cabecera">
      <div>
        <div className="detalle-titulo-fila">
          <h1>{lote.nombre}</h1>
          <button
            type="button"
            className="detalle-editar-btn"
            title="Editar lote"
            aria-label="Editar lote"
            onClick={() => setEditandoLote(true)}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
          </button>
        </div>
        <div className="detalle-subtitulo">
          {cultivoMasReciente(lote) && (
            <span className={`cultivo-badge cultivo-${cultivoMasReciente(lote).tipo_cultivo}`}>
              {etiquetaTipoCultivo(cultivoMasReciente(lote).tipo_cultivo)}
            </span>
          )}
          {lote.area_ha && <span>{lote.area_ha.toLocaleString('es-AR', { maximumFractionDigits: 1 })} ha</span>}
          {suelo && <span>Suelo: {suelo}</span>}
          {ultimoVuelo && <span>Último vuelo: {ultimoVuelo}</span>}
        </div>
      </div>
      <button type="button" className="btn-primary" onClick={() => setNuevoAnalisisAbierto(true)}>
        + Cargar Ortomosaico
      </button>
    </div>
  )

  return (
    <PanelLayout
      migas={[{ label: 'Lotes', to: '/lotes' }, { label: lote.nombre }]}
      onVerDiagnosticos={() => navigate(`/lotes/${loteId}`)}
    >
      <main className={`detalle-main ${vista === 'calendario' ? 'detalle-main--calendario' : ''}`}>
        {cabecera}
        {contenido}
      </main>

      {editandoLote && (
        <ModalEditarLote
          lote={lote}
          onSuccess={() => { setEditandoLote(false); cargarLote(); avisar('Lote actualizado') }}
          onClose={() => setEditandoLote(false)}
        />
      )}

      {vueloParaEditar && (
        <ModalEditarVuelo
          loteId={loteId}
          vuelo={vueloParaEditar}
          cultivos={lote.cultivos || []}
          onSuccess={() => { setVueloParaEditar(null); cargarLote(); avisar('Vuelo actualizado') }}
          onClose={() => setVueloParaEditar(null)}
        />
      )}

      {vueloParaEliminar && (
        <ModalConfirmarEliminar
          titulo="Eliminar vuelo"
          mensaje="¿Seguro que querés eliminar este vuelo y su análisis? Esta acción no se puede deshacer."
          onConfirmar={handleEliminarVuelo}
          onClose={() => setVueloParaEliminar(null)}
        />
      )}

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
