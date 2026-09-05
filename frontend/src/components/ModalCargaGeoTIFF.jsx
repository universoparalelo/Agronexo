import { useEffect, useRef, useState } from 'react'
import client from '../api/client'
import { analizarIndicesBatch, inspeccionarGeotiff } from '../api/analisis'

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
  const [sensor, setSensor] = useState('sentinel2')
  const [indices, setIndices] = useState(() => indicesAutomaticos('sentinel2'))
  const [indiceMostrado, setIndiceMostrado] = useState('ndvi')
  const [archivo, setArchivo] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadPhase, setUploadPhase] = useState(null) // 'uploading' | 'processing' | 'done'
  const [error, setError] = useState('')
  const [inspeccion, setInspeccion] = useState(null)
  const inputRef = useRef()

  const sinLotes = !lotes || lotes.length === 0
  const loteSeleccionado = lotes?.find((l) => l.id === loteId)
  const indiceInfo = INDICES.find((i) => i.value === indiceMostrado)
  const indicesParaSensor = indicesDisponibles(sensor)

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

  function toggleIndice(value) {
    // cada clic (prenda o apague el índice) siempre actualiza la info mostrada
    setIndiceMostrado(value)
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
    if (!archivo) { setError('Seleccioná un archivo GeoTIFF.'); return }
    setError('')
    setStep('analisis')
  }

  function uploadMessage() {
    if (uploadPhase === 'processing') return 'Archivo recibido. Encolando análisis...'
    if (uploadPhase === 'done') return 'El análisis estará listo en unos momentos.'
    if (uploadProgress < 15) return 'Iniciando carga del ortomosaico...'
    if (uploadProgress < 40) return 'Subiendo archivo, aguarde un momento...'
    if (uploadProgress < 70) return 'Cargando ortomosaico...'
    if (uploadProgress < 95) return 'Casi listo, finalizando la carga...'
    return 'Procesando archivo en el servidor...'
  }

  async function handleSubmit() {
    const fd = new FormData()
    fd.append('archivo', archivo)
    fd.append('sensor', sensor)

    setLoading(true)
    setError('')
    setUploadProgress(0)
    setUploadPhase('uploading')
    try {
      const { data } = await client.post(`/lotes/${loteId}/vuelos`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) {
            setUploadProgress(Math.round((e.loaded / e.total) * 100))
          }
        },
      })

      setUploadPhase('processing')
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
      setError(typeof msg === 'string' ? msg : 'Error al subir el archivo. Verificá que sea un GeoTIFF válido.')
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

            {error && <p className="error-message">{error}</p>}

            <div className="modal-actions modal-actions--wizard">
              <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
                Cancelar
              </button>
              <button type="button" className="btn-primary" onClick={handleSiguiente} disabled={!archivo}>
                Siguiente →
              </button>
            </div>
          </div>
        ) : (
          <div className="modal-form">
            <p className="config-analisis-titulo">Análisis del ortomosaico</p>

            <div className="lote-info-card">
              <div className="lote-info-thumb"><IconDron /></div>
              <div className="lote-info-body">
                <div className="lote-info-title-row">
                  <h3>{loteSeleccionado?.nombre}</h3>
                  <span className="lote-info-badge">Cargado</span>
                </div>
                <div className="lote-info-meta">
                  <span><strong>Superficie:</strong> {loteSeleccionado?.area_ha ? `${Math.round(loteSeleccionado.area_ha)} Ha` : '—'}</span>
                  <span><strong>Cultivo:</strong> {CULTIVO_LABEL[loteSeleccionado?.cultivo] ?? loteSeleccionado?.cultivo}</span>
                  <span><strong>Sensor:</strong> {SENSOR_LABEL[sensor]}</span>
                  <span><strong>Archivo:</strong> {archivo?.name}</span>
                </div>
              </div>
            </div>

            <div className="config-analisis-header">
              <p className="config-analisis-titulo">Configuración de análisis</p>
              <p className="config-analisis-sub">
                NDVI, NDRE, SAVI y GNDVI se calculan automáticamente. Destildá los que no necesites o sumá ExG.
              </p>
            </div>

            <div className="indice-grid" style={{ gridTemplateColumns: `repeat(${indicesParaSensor.length}, 1fr)` }}>
              {indicesParaSensor.map((i) => (
                <button
                  type="button"
                  key={i.value}
                  className={`indice-btn${indices.includes(i.value) ? ' indice-btn--active' : ''}`}
                  onClick={() => toggleIndice(i.value)}
                  aria-pressed={indices.includes(i.value)}
                >
                  <span className="indice-btn-label">{i.label}</span>
                  <span className="indice-btn-sub">{i.sub}</span>
                </button>
              ))}
            </div>

            {indiceInfo && (
              <div className="indice-desc-box">
                <IconInfo />
                <p><strong>{indiceInfo.label}</strong> — {indiceInfo.desc}</p>
              </div>
            )}

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
