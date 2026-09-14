import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import client from '../api/client'
import CalendarioSatelital from './CalendarioSatelital'
import {
  analizarIndicesBatch,
  buscarImagenesSatelitales,
  crearVueloDesdeSatelite,
  inspeccionarGeotiff,
} from '../api/analisis'

// Mismo patrón que ModalLimites.jsx/ModalNuevoLote.jsx — autocentra el mapa
// en una geometría ya conocida, sin depender de props extra de Leaflet.
function FitBounds({ bounds }) {
  const map = useMap()
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [20, 20] })
  }, [bounds, map])
  return null
}

function boundsDesdePoligono(coordinates) {
  const coords = coordinates[0]
  const lngs = coords.map((c) => c[0])
  const lats = coords.map((c) => c[1])
  return [
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)],
  ]
}

const CULTIVO_LABEL = { soja: 'Soja', maiz: 'Maíz', algodon: 'Algodón', sorgo: 'Sorgo' }

const SENSORES = [
  { value: 'sentinel2', label: 'Sentinel-2' },
  { value: 'dji_mavic3', label: 'DJI Mavic 3 Multispectral' },
]

const SENSOR_LABEL = Object.fromEntries(SENSORES.map((s) => [s.value, s.label]))

// Solo los índices que el worker GIS ya calcula (workers/gis/band_mapping.py),
// con las bandas que necesita cada uno (BANDAS_POR_INDICE en ese mismo archivo).
const INDICES = [
  {
    value: 'ndvi', label: 'NDVI', sub: 'NIR / RED', bandas: ['NIR', 'RED'],
    desc: 'Índice de Vegetación de Diferencia Normalizada. Ideal para crecimiento vegetativo (25–60 días desde siembra).',
  },
  {
    value: 'ndre', label: 'NDRE', sub: 'NIR / RE', bandas: ['NIR', 'RE'],
    desc: 'Índice de Borde Rojo Normalizado. Detección temprana de estrés clorofílico y de nitrógeno, antes de que el NDVI muestre diferencias.',
  },
  {
    value: 'savi', label: 'SAVI', sub: 'NIR / RED', bandas: ['NIR', 'RED'],
    desc: 'Índice Ajustado al Suelo. Recomendado en las primeras 3 semanas post-siembra, cuando la cobertura vegetal es menor al 30% y el suelo está expuesto.',
  },
  {
    value: 'gndvi', label: 'GNDVI', sub: 'NIR / GREEN', bandas: ['NIR', 'GREEN'],
    desc: 'Índice Verde Normalizado. Más sensible que el NDVI cuando este ya satura (> 0.75), útil en floración/llenado de grano.',
  },
  {
    value: 'exg', label: 'ExG', sub: 'RGB', bandas: ['GREEN', 'RED', 'BLUE'],
    desc: 'Exceso de Verde. Usa solo bandas visibles (RGB) para diferenciar vegetación de suelo desnudo — útil con cámaras sin banda NIR. No se calcula automáticamente: hay que seleccionarlo a mano.',
  },
]

// Todos los índices disponibles para el sensor, salvo ExG — se calculan
// automáticamente al subir el vuelo sin que el usuario tenga que tildarlos.
function indicesAutomaticos(sensor) {
  return indicesDisponibles(sensor).filter((i) => i.value !== 'exg').map((i) => i.value)
}

// Bandas disponibles por sensor (workers/gis/band_mapping.py::MAPEO_SENSORES).
// El DJI Mavic 3 Multispectral real no tiene banda Blue.
const BANDAS_POR_SENSOR = {
  sentinel2: ['BLUE', 'GREEN', 'RED', 'RE', 'NIR'],
  dji_mavic3: ['GREEN', 'RED', 'RE', 'NIR'],
}

function indicesDisponibles(sensor) {
  const disponibles = BANDAS_POR_SENSOR[sensor] ?? []
  return INDICES.filter((i) => i.bandas.every((b) => disponibles.includes(b)))
}

const IconUpload = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
    <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
  </svg>
)
const IconSearch = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
)
const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
)
const IconInfo = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
  </svg>
)
const IconSatelite = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <rect x="8" y="8" width="8" height="8" rx="1.5" transform="rotate(45 12 12)"/>
    <line x1="14.5" y1="9.5" x2="19" y2="5"/>
    <line x1="9.5" y1="14.5" x2="5" y2="19"/>
    <path d="M2 22l3-3"/>
    <path d="M17 2l-1.5 1.5"/>
    <path d="M4 7l3 3"/>
  </svg>
)
const IconDron = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9.5" y="9.5" width="5" height="5" rx="1"/>
    <line x1="9.5" y1="9.5" x2="4" y2="4"/>
    <line x1="14.5" y1="9.5" x2="20" y2="4"/>
    <line x1="9.5" y1="14.5" x2="4" y2="20"/>
    <line x1="14.5" y1="14.5" x2="20" y2="20"/>
    <circle cx="4" cy="4" r="2.2"/>
    <circle cx="20" cy="4" r="2.2"/>
    <circle cx="4" cy="20" r="2.2"/>
    <circle cx="20" cy="20" r="2.2"/>
  </svg>
)

export default function ModalCargaGeoTIFF({ lotes, loteIdInicial, onSuccess, onClose }) {
  const [step, setStep] = useState('carga') // 'carga' | 'analisis'
  const [loteId, setLoteId] = useState(loteIdInicial ?? lotes?.[0]?.id ?? '')
  const [fuente, setFuente] = useState('dron') // 'dron' | 'satelite'
  const [sensor, setSensor] = useState('sentinel2')
  const [indices, setIndices] = useState(() => indicesAutomaticos('sentinel2'))
  const [indiceMostrado, setIndiceMostrado] = useState('ndvi')
  const [archivo, setArchivo] = useState(null)
  const [estadioFenologico, setEstadioFenologico] = useState('')
  const [fechaVuelo, setFechaVuelo] = useState('')
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadPhase, setUploadPhase] = useState(null) // 'uploading' | 'processing' | 'done'
  const [error, setError] = useState('')
  const [inspeccion, setInspeccion] = useState(null)
  const inputRef = useRef()

  // ── Carga desde imagen satelital (sin subir archivo) ──────────────────
  const [fechaDeseada, setFechaDeseada] = useState('')
  const [buscandoEscenas, setBuscandoEscenas] = useState(false)
  const [errorBusqueda, setErrorBusqueda] = useState('')
  const [escenas, setEscenas] = useState([])
  const [escenaSeleccionada, setEscenaSeleccionada] = useState(null)

  const sinLotes = !lotes || lotes.length === 0
  const loteSeleccionado = lotes?.find((l) => l.id === loteId)
  const indiceInfo = INDICES.find((i) => i.value === indiceMostrado)
  const indicesParaSensor = indicesDisponibles(sensor)
  const loteBoundsSatelital = loteSeleccionado?.geometry
    ? boundsDesdePoligono(loteSeleccionado.geometry.coordinates)
    : null

  useEffect(() => {
    // al cambiar de sensor, recalculamos qué índices se calculan por
    // defecto (ej: ExG queda afuera con dji_mavic3, que no tiene Blue)
    const automaticos = indicesAutomaticos(sensor)
    setIndices(automaticos)
    if (!automaticos.includes(indiceMostrado)) {
      setIndiceMostrado(automaticos[0] ?? 'ndvi')
    }
  }, [sensor]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!archivo) { setInspeccion(null); return }
    let cancelado = false
    inspeccionarGeotiff(archivo, sensor)
      .then((data) => { if (!cancelado) setInspeccion(data) })
      .catch(() => { if (!cancelado) setInspeccion(null) })
    return () => { cancelado = true }
  }, [archivo, sensor])

  useEffect(() => {
    // al cambiar de lote, sugerimos su estadio como punto de partida — pero
    // sigue siendo editable, es el estadio de ESTE vuelo puntual, no el del
    // lote (ver app/diagnostico/service.py::_resolver_estadio).
    setEstadioFenologico(loteSeleccionado?.estadio_fenologico ?? '')
    // resultados de búsqueda satelital son específicos del lote anterior —
    // no tiene sentido dejarlos si se cambia de lote a mitad de camino.
    setFechaDeseada('')
    setEscenas([])
    setEscenaSeleccionada(null)
    setErrorBusqueda('')
  }, [loteId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // la imagen satelital siempre viene de Sentinel-2 — no hay selección
    // manual de sensor en este modo, a diferencia de subir un archivo.
    if (fuente === 'satelite') setSensor('sentinel2')
  }, [fuente])

  function cambiarFuente(nueva) {
    setFuente(nueva)
    setArchivo(null)
    setEscenas([])
    setEscenaSeleccionada(null)
    setErrorBusqueda('')
    setError('')
  }

  async function handleBuscarEscenas(fechaParam) {
    const fecha = fechaParam ?? fechaDeseada
    if (!fecha) {
      setErrorBusqueda('Elegí una fecha para buscar.')
      return
    }
    setBuscandoEscenas(true)
    setErrorBusqueda('')
    setEscenas([])
    setEscenaSeleccionada(null)
    try {
      const data = await buscarImagenesSatelitales(loteId, fecha, 15)
      setEscenas(data.items)
      if (data.items.length > 0) setEscenaSeleccionada(data.items[0])
    } catch (err) {
      const msg = err.response?.data?.detail
      setErrorBusqueda(typeof msg === 'string' ? msg : 'No se pudieron buscar imágenes satelitales. Probá de nuevo.')
    } finally {
      setBuscandoEscenas(false)
    }
  }

  function handleElegirFechaCalendario(fechaISO) {
    setFechaDeseada(fechaISO)
    handleBuscarEscenas(fechaISO)
  }

  function toggleIndice(value) {
    // cada clic (prenda o apague el índice) siempre actualiza la info mostrada
    setIndiceMostrado(value)
    // NDVI se calcula siempre al subir el vuelo (crear_vuelo_desde_upload lo
    // encola sin mirar esta selección) — no es opcional, así que no se puede
    // destildar. Ver app/ingesta/service.py.
    if (value === 'ndvi') return
    setIndices((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    )
  }

  function handleArchivo(file) {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (ext !== 'tif' && ext !== 'tiff') {
      setError('El archivo debe ser un GeoTIFF (.tif o .tiff).')
      return
    }
    setError('')
    setArchivo(file)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleArchivo(e.dataTransfer.files[0])
  }

  function handleSiguiente() {
    if (!loteId) { setError('Seleccioná a qué lote pertenece este vuelo.'); return }
    if (fuente === 'dron' && !archivo) { setError('Seleccioná un archivo GeoTIFF.'); return }
    if (fuente === 'satelite' && !escenaSeleccionada) { setError('Elegí una escena satelital.'); return }
    if (fuente === 'satelite') setFechaVuelo(escenaSeleccionada.fecha)
    setError('')
    setStep('analisis')
  }

  function uploadMessage() {
    if (fuente === 'satelite') {
      if (uploadPhase === 'processing') return 'Descargando y recortando la imagen satelital...'
      if (uploadPhase === 'done') return 'El análisis estará listo en unos momentos.'
      return 'Solicitando imagen satelital...'
    }
    if (uploadPhase === 'processing') return 'Archivo recibido. Encolando análisis...'
    if (uploadPhase === 'done') return 'El análisis estará listo en unos momentos.'
    if (uploadProgress < 15) return 'Iniciando carga del ortomosaico...'
    if (uploadProgress < 40) return 'Subiendo archivo, aguarde un momento...'
    if (uploadProgress < 70) return 'Cargando ortomosaico...'
    if (uploadProgress < 95) return 'Casi listo, finalizando la carga...'
    return 'Procesando archivo en el servidor...'
  }

  async function handleSubmit() {
    setLoading(true)
    setError('')

    try {
      let data
      if (fuente === 'satelite') {
        // No hay bytes que subir — la descarga real ocurre en el worker
        // (workers.gis.tasks.descargar_satelital), así que no hay barra de
        // progreso de upload, directo a "procesando".
        setUploadPhase('processing')
        data = await crearVueloDesdeSatelite(
          loteId,
          escenaSeleccionada.escena_id,
          new Date(fechaVuelo).toISOString(),
          estadioFenologico.trim() || null,
        )
      } else {
        const fd = new FormData()
        fd.append('archivo', archivo)
        fd.append('sensor', sensor)
        if (estadioFenologico.trim()) fd.append('estadio_fenologico', estadioFenologico.trim())
        if (fechaVuelo) fd.append('fecha_vuelo', new Date(fechaVuelo).toISOString())

        setUploadProgress(0)
        setUploadPhase('uploading')
        const res = await client.post(`/lotes/${loteId}/vuelos`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (e) => {
            if (e.total) {
              setUploadProgress(Math.round((e.loaded / e.total) * 100))
            }
          },
        })
        data = res.data
        setUploadPhase('processing')
      }

      const indicesAdicionales = indices.filter((i) => i !== 'ndvi')
      if (indicesAdicionales.length > 0) {
        try {
          await analizarIndicesBatch(loteId, data.vuelo_id, indicesAdicionales)
        } catch {
          // no bloquear la creación del vuelo si falla encolar los índices
        }
      }
      setUploadPhase('done')
      onSuccess(data)
    } catch (err) {
      const msg = err.response?.data?.detail
      const fallback = fuente === 'satelite'
        ? 'Error al solicitar la imagen satelital. Probá de nuevo.'
        : 'Error al subir el archivo. Verificá que sea un GeoTIFF válido.'
      setError(typeof msg === 'string' ? msg : fallback)
      setUploadPhase(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--wizard" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Nuevo análisis de ortomosaico</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">×</button>
        </div>

        {!sinLotes && (
          <div className="wizard-stepper">
            <div className={`wizard-step${step === 'carga' ? ' wizard-step--active' : ' wizard-step--done'}`}>
              <span className="wizard-step-icon">{step === 'carga' ? <IconUpload /> : <IconCheck />}</span>
              <span className="wizard-step-label">Carga</span>
            </div>
            <div className={`wizard-step-line${step === 'analisis' ? ' wizard-step-line--done' : ''}`} />
            <div className={`wizard-step${step === 'analisis' ? ' wizard-step--active' : ''}`}>
              <span className="wizard-step-icon"><IconSearch /></span>
              <span className="wizard-step-label">Análisis</span>
            </div>
          </div>
        )}

        {sinLotes ? (
          <div className="modal-form">
            <p className="empty-hint">
              Todavía no tenés lotes registrados. Creá un lote primero con "Nuevo Lote".
            </p>
            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={onClose}>Cerrar</button>
            </div>
          </div>
        ) : step === 'carga' ? (
          <div className="modal-form">
            <div className="form-group">
              <label htmlFor="lote">Lote</label>
              <select
                id="lote"
                value={loteId}
                onChange={(e) => setLoteId(e.target.value)}
                disabled={loading}
              >
                {lotes.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.nombre} — {CULTIVO_LABEL[l.cultivo] ?? l.cultivo}
                  </option>
                ))}
              </select>
            </div>

            <div className="modo-limite-toggle">
              <button
                type="button"
                className={`modo-limite-btn${fuente === 'dron' ? ' modo-limite-btn--activo' : ''}`}
                onClick={() => cambiarFuente('dron')}
                disabled={loading}
              >
                🚁 Subir archivo (dron)
              </button>
              <button
                type="button"
                className={`modo-limite-btn${fuente === 'satelite' ? ' modo-limite-btn--activo' : ''}`}
                onClick={() => cambiarFuente('satelite')}
                disabled={loading || !loteSeleccionado?.geometry}
                title={!loteSeleccionado?.geometry ? 'Este lote no tiene límite cargado — dibujalo primero para poder usar imágenes satelitales.' : undefined}
              >
                🛰️ Imagen satelital
              </button>
            </div>
            {fuente === 'satelite' && !loteSeleccionado?.geometry && (
              <p className="area-badge area-badge--alerta">
                Este lote no tiene límite cargado — dibujalo primero (botón "Límites") para poder recortar una imagen satelital.
              </p>
            )}

            {fuente === 'dron' ? (
              <>
                <div className="form-group">
                  <label htmlFor="sensor">Sensor</label>
                  <select
                    id="sensor"
                    value={sensor}
                    onChange={(e) => setSensor(e.target.value)}
                    disabled={loading}
                  >
                    {SENSORES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>

                {inspeccion && !inspeccion.compatible ? (
                  <div className="requisitos-box requisitos-box--error">
                    <IconInfo />
                    <p>
                      <strong>El archivo no coincide con el sensor seleccionado</strong><br />
                      {inspeccion.mensaje}
                    </p>
                  </div>
                ) : (
                  <div className="requisitos-box">
                    <IconInfo />
                    <p>
                      <strong>Requerimientos Técnicos</strong><br />
                      El archivo debe estar en formato GeoTIFF (.tif), contener información georreferenciada y poseer
                      las bandas necesarias para el análisis multiespectral.
                    </p>
                  </div>
                )}

                <div
                  className={`dropzone${dragging ? ' dropzone--activo' : ''}${archivo ? ' dropzone--ok' : ''}`}
                  onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => inputRef.current.click()}
                >
                  <input
                    ref={inputRef}
                    type="file"
                    accept=".tif,.tiff"
                    style={{ display: 'none' }}
                    onChange={(e) => handleArchivo(e.target.files[0])}
                  />
                  {archivo ? (
                    <p className="dropzone-archivo">{archivo.name}</p>
                  ) : (
                    <>
                      <p className="dropzone-icono">☁️</p>
                      <p className="dropzone-hint">Arrastrá el archivo GeoTIFF aquí</p>
                      <p className="dropzone-hint dropzone-hint--sub">O hacé clic para explorar tus archivos locales</p>
                      <p className="dropzone-ext">.tif / .tiff</p>
                    </>
                  )}
                </div>
              </>
            ) : (
              <>
                {loteBoundsSatelital && (
                  <div className="limites-preview-map">
                    <MapContainer
                      bounds={loteBoundsSatelital}
                      style={{ height: '220px', width: '100%', borderRadius: '8px' }}
                      zoomControl={true}
                      scrollWheelZoom={false}
                    >
                      <TileLayer
                        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                        attribution="Tiles &copy; Esri"
                      />
                      <GeoJSON
                        data={loteSeleccionado.geometry}
                        style={{ color: '#2ecc71', weight: 2, fillOpacity: 0.15 }}
                      />
                      <FitBounds bounds={loteBoundsSatelital} />
                    </MapContainer>
                  </div>
                )}

                <div className="form-group">
                  <label>Fecha deseada</label>
                  <CalendarioSatelital
                    loteId={loteId}
                    fechaSeleccionada={fechaDeseada}
                    onSeleccionar={handleElegirFechaCalendario}
                    disabled={loading || buscandoEscenas}
                  />
                </div>

                {buscandoEscenas && <p className="dropzone-hint dropzone-hint--sub">Buscando imágenes para esa fecha...</p>}
                {errorBusqueda && <p className="error-message">{errorBusqueda}</p>}

                {escenas.length > 0 && (
                  <div className="escena-satelital-lista">
                    <p className="dropzone-hint dropzone-hint--sub">
                      Elegí una fecha — si está muy nublada, probá otra.
                    </p>
                    {escenas.map((e) => (
                      <button
                        type="button"
                        key={e.escena_id}
                        className={`escena-satelital-card${escenaSeleccionada?.escena_id === e.escena_id ? ' escena-satelital-card--activa' : ''}${e.nubes_pct != null && e.nubes_pct > 30 ? ' escena-satelital-card--nublada' : ''}`}
                        onClick={() => setEscenaSeleccionada(e)}
                        disabled={loading}
                      >
                        {e.thumbnail_url && (
                          <img className="escena-satelital-thumb" src={e.thumbnail_url} alt={`Vista previa de la escena del ${e.fecha}`} loading="lazy" />
                        )}
                        <span className="escena-satelital-fecha">{e.fecha}</span>
                        <span className="escena-satelital-nubes">
                          ☁️ {e.nubes_pct != null ? `${e.nubes_pct.toFixed(1)}%` : '—'}
                        </span>
                        <span className="escena-satelital-dias">{e.dias_diferencia === 0 ? 'exacta' : `±${e.dias_diferencia} día(s)`}</span>
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}

            {error && <p className="error-message">{error}</p>}

            <div className="modal-actions modal-actions--wizard">
              <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
                Cancelar
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={handleSiguiente}
                disabled={fuente === 'dron' ? !archivo : !escenaSeleccionada}
              >
                Siguiente →
              </button>
            </div>
          </div>
        ) : (
          <div className="modal-form">
            <p className="config-analisis-titulo">Análisis del ortomosaico</p>

            <div className="lote-info-card">
              <div className="lote-info-thumb">{fuente === 'satelite' ? <IconSatelite /> : <IconDron />}</div>
              <div className="lote-info-body">
                <div className="lote-info-title-row">
                  <h3>{loteSeleccionado?.nombre}</h3>
                  <span className="lote-info-badge">Cargado</span>
                </div>
                <div className="lote-info-meta">
                  <span><strong>Superficie:</strong> {loteSeleccionado?.area_ha ? `${Math.round(loteSeleccionado.area_ha)} Ha` : '—'}</span>
                  <span><strong>Cultivo:</strong> {CULTIVO_LABEL[loteSeleccionado?.cultivo] ?? loteSeleccionado?.cultivo}</span>
                  <span><strong>Sensor:</strong> {SENSOR_LABEL[sensor]}</span>
                  {fuente === 'satelite' ? (
                    <span><strong>Escena:</strong> {escenaSeleccionada?.fecha} ({escenaSeleccionada?.nubes_pct != null ? `${escenaSeleccionada.nubes_pct.toFixed(1)}% nubes` : 'nubes desconocidas'})</span>
                  ) : (
                    <span><strong>Archivo:</strong> {archivo?.name}</span>
                  )}
                </div>
              </div>
            </div>

            <div className="config-analisis-header">
              <p className="config-analisis-titulo">Configuración de análisis</p>
              <p className="config-analisis-sub">
                NDVI se calcula siempre (es la base del diagnóstico). NDRE, SAVI y GNDVI vienen tildados por defecto — destildá los que no necesites o sumá ExG.
              </p>
            </div>

            <div className="indice-grid" style={{ gridTemplateColumns: `repeat(${indicesParaSensor.length}, 1fr)` }}>
              {indicesParaSensor.map((i) => (
                <button
                  type="button"
                  key={i.value}
                  className={`indice-btn${indices.includes(i.value) ? ' indice-btn--active' : ''}${i.value === 'ndvi' ? ' indice-btn--locked' : ''}`}
                  onClick={() => toggleIndice(i.value)}
                  aria-pressed={indices.includes(i.value)}
                  title={i.value === 'ndvi' ? 'NDVI se calcula siempre al subir el vuelo — es la base del diagnóstico y no se puede destildar.' : undefined}
                >
                  <span className="indice-btn-label">{i.label}</span>
                  <span className="indice-btn-sub">{i.value === 'ndvi' ? 'Siempre incluido' : i.sub}</span>
                </button>
              ))}
            </div>

            {indiceInfo && (
              <div className="indice-desc-box">
                <IconInfo />
                <p><strong>{indiceInfo.label}</strong> — {indiceInfo.desc}</p>
              </div>
            )}

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="estadio_vuelo">Estadio fenológico <span className="label-opcional">(opcional)</span></label>
                <input
                  id="estadio_vuelo"
                  type="text"
                  placeholder="Ej: R3"
                  maxLength={30}
                  value={estadioFenologico}
                  onChange={(e) => setEstadioFenologico(e.target.value)}
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="fecha_vuelo">
                  Fecha del vuelo {fuente === 'dron' && <span className="label-opcional">(opcional)</span>}
                </label>
                <input
                  id="fecha_vuelo"
                  type="date"
                  value={fechaVuelo}
                  onChange={(e) => setFechaVuelo(e.target.value)}
                  disabled={loading || fuente === 'satelite'}
                  title={fuente === 'satelite' ? 'Es la fecha real de captura de la escena elegida — no se puede editar.' : undefined}
                />
              </div>
            </div>

            {error && <p className="error-message">{error}</p>}

            {loading && (
              <div className="upload-progress-wrapper">
                <div className="upload-progress-bar-bg">
                  <div
                    className="upload-progress-bar-fill"
                    style={{ width: `${uploadPhase === 'processing' || uploadPhase === 'done' ? 100 : uploadProgress}%` }}
                  />
                </div>
                <div className="upload-progress-info">
                  <span className="upload-progress-msg">{uploadMessage()}</span>
                  {uploadPhase === 'uploading' && (
                    <span className="upload-progress-pct">{uploadProgress}%</span>
                  )}
                </div>
              </div>
            )}

            <div className="modal-actions modal-actions--wizard">
              <button type="button" className="btn-secondary" onClick={() => setStep('carga')} disabled={loading}>
                ← Atrás
              </button>
              <button type="button" className="btn-primary" onClick={handleSubmit} disabled={loading}>
                {loading ? 'Subiendo...' : 'Iniciar Análisis →'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
