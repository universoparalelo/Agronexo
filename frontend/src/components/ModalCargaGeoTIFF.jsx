import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import client from '../api/client'
import CalendarioSatelital from './CalendarioSatelital'
import MapaDibujoLote from './MapaDibujoLote'
import MapaNEA from './MapaNEA'
import { FlechaAtras, FlechaAdelante } from './BotonVolver'
import { geotiffCercaDelLote, leerLimitesGeotiff } from '../utils/geotiffLimites'
import { AREA_MIN_HA, AREA_MAX_HA } from '../utils/geometria'
import { TIPOS_SUELO } from '../utils/suelos'
import { CULTIVOS, cultivoMasReciente, descripcionCultivo, etiquetaTipoCultivo } from '../utils/cultivos'
import {
  analizarIndicesBatch,
  buscarImagenesSatelitales,
  crearVueloDesdeSatelite,
  inspeccionarGeotiff,
  listarEstadiosFenologicos,
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

const MSG_FUERA_DEL_LOTE = 'GeoTIFF subido queda por fuera de los límites guardados del lote.'

const CULTIVO_NUEVO = '__nuevo__'

const CULTIVO_NUEVO_VACIO = { tipo_cultivo: '', variedad: '', fecha_siembra: '', fecha_cosecha: '' }

const aInputFecha = (iso) => (iso ? iso.slice(0, 10) : '')

function formDesdeCultivo(c) {
  return {
    tipo_cultivo: c.tipo_cultivo,
    variedad: c.variedad ?? '',
    fecha_siembra: aInputFecha(c.fecha_siembra),
    fecha_cosecha: aInputFecha(c.fecha_cosecha),
  }
}

function fmtFechaCultivo(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' })
}

const SENSOR_POR_DEFECTO = 'dji_mavic3'

const SENSORES = [
  { value: 'dji_mavic3', label: 'DJI Mavic 3 Multispectral' },
  { value: 'sentinel2', label: 'Sentinel-2' },
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
    desc: 'Exceso de Verde (normalizado por el brillo, no cambia con la iluminación). Usa solo bandas visibles (RGB) para diferenciar vegetación de suelo desnudo — útil con cámaras sin banda NIR.',
  },
]

// Todos los índices que el sensor permite calcular arrancan seleccionados.
// ExG necesita la banda Blue, que el DJI Mavic 3 no captura — para ese sensor
// simplemente no se ofrece (ver band_mapping.py).
function indicesAutomaticos(sensor) {
  return indicesDisponibles(sensor).map((i) => i.value)
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
const IconSatelite = ({ size = 26 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <g transform="rotate(-45 12 12)">
      <rect x="9.5" y="9.5" width="5" height="5" rx="1"/>
      <rect x="1.5" y="9.7" width="6" height="4.6" rx="0.6"/>
      <rect x="16.5" y="9.7" width="6" height="4.6" rx="0.6"/>
      <line x1="7.5" y1="12" x2="9.5" y2="12"/>
      <line x1="14.5" y1="12" x2="16.5" y2="12"/>
      <line x1="12" y1="9.5" x2="12" y2="7"/>
      <circle cx="12" cy="6.2" r="0.9"/>
    </g>
  </svg>
)
const IconDron = ({ size = 26 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="8.5" y="10" width="7" height="4.5" rx="1.6"/>
    <circle cx="12" cy="16.6" r="1.3"/>
    <line x1="8.5" y1="11.2" x2="5.2" y2="7.6"/>
    <line x1="15.5" y1="11.2" x2="18.8" y2="7.6"/>
    <line x1="8.5" y1="13.3" x2="5.2" y2="16.9"/>
    <line x1="15.5" y1="13.3" x2="18.8" y2="16.9"/>
    <ellipse cx="5.2" cy="6.6" rx="3.2" ry="1"/>
    <ellipse cx="18.8" cy="6.6" rx="3.2" ry="1"/>
    <ellipse cx="5.2" cy="17.9" rx="3.2" ry="1"/>
    <ellipse cx="18.8" cy="17.9" rx="3.2" ry="1"/>
  </svg>
)
const IconHoja = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 20A7 7 0 019.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/>
    <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
  </svg>
)

function AyudaVariedad() {
  return (
    <span className="ayuda-tip">
      <button type="button" className="ayuda-tip-boton" aria-label="¿Qué es la variedad?">?</button>
      <span role="tooltip" className="ayuda-tip-caja">
        La variedad de una semilla es su versión comercial dentro del cultivo (ej: DM 46i17).
      </span>
    </span>
  )
}

function CultivoDropdown({ cultivos, seleccion, creando, onElegir, onNuevo, disabled }) {
  const [abierto, setAbierto] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!abierto) return
    const cerrarSiClickAfuera = (e) => { if (ref.current && !ref.current.contains(e.target)) setAbierto(false) }
    document.addEventListener('mousedown', cerrarSiClickAfuera)
    return () => document.removeEventListener('mousedown', cerrarSiClickAfuera)
  }, [abierto])

  const elegido = cultivos.find((c) => c.id === seleccion)

  const detalle = (c) => (
    <span className="cultivo-item-texto">
      <span className="cultivo-item-nombre">{etiquetaTipoCultivo(c.tipo_cultivo)}</span>
      <span className="cultivo-item-fechas">
        Variedad: {c.variedad || '—'} · Siembra: {fmtFechaCultivo(c.fecha_siembra)} · Cosecha: {fmtFechaCultivo(c.fecha_cosecha)}
      </span>
    </span>
  )

  return (
    <div className="cultivo-dropdown" ref={ref}>
      <button
        type="button"
        className="cultivo-item cultivo-item--activo cultivo-dropdown-trigger"
        onClick={() => setAbierto((a) => !a)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={abierto}
      >
        {elegido ? detalle(elegido) : (
          <span className="cultivo-item-texto">
            <span className="cultivo-item-nombre">{creando ? 'Cultivo nuevo' : 'Seleccioná un cultivo'}</span>
            <span className="cultivo-item-fechas">
              {creando ? 'Completá los datos de abajo' : `${cultivos.length} cultivo${cultivos.length !== 1 ? 's' : ''} en este lote`}
            </span>
          </span>
        )}
        <span className="cultivo-dropdown-flecha" aria-hidden="true">▾</span>
      </button>

      {abierto && (
        <div className="cultivo-dropdown-panel">
          <div className="cultivo-dropdown-lista" role="listbox">
            {cultivos.length === 0 && (
              <p className="cultivo-dropdown-vacio">Este lote todavía no tiene cultivos cargados.</p>
            )}
            {cultivos.map((c) => (
              <button
                type="button"
                key={c.id}
                role="option"
                aria-selected={seleccion === c.id}
                className={`cultivo-item${seleccion === c.id ? ' cultivo-item--activo' : ''}`}
                onClick={() => { onElegir(c); setAbierto(false) }}
              >
                {detalle(c)}
              </button>
            ))}
          </div>
          <button
            type="button"
            className={`cultivo-item cultivo-item--nuevo${creando ? ' cultivo-item--activo' : ''}`}
            onClick={() => { onNuevo(); setAbierto(false) }}
          >
            ＋ Nuevo cultivo
          </button>
        </div>
      )}
    </div>
  )
}

const PASOS = [
  { key: 'carga', label: 'Carga', icon: <IconUpload /> },
  { key: 'cultivo', label: 'Cultivo', icon: <IconHoja /> },
  { key: 'analisis', label: 'Análisis', icon: <IconSearch /> },
]

export default function ModalCargaGeoTIFF({ lotes, loteIdInicial, onSuccess, onClose, onLoteCreado }) {
  const [step, setStep] = useState('carga') // 'carga' | 'cultivo' | 'analisis'
  const [loteId, setLoteId] = useState(loteIdInicial ?? '')
  const [fuente, setFuente] = useState('dron') // 'dron' | 'satelite'
  const [sensor, setSensor] = useState(SENSOR_POR_DEFECTO)
  const [indices, setIndices] = useState(() => indicesAutomaticos(SENSOR_POR_DEFECTO))
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
  const [limitesGeotiff, setLimitesGeotiff] = useState(null)
  // Todo análisis se hace sobre un cultivo: uno ya cargado en el lote o uno nuevo.
  const [cultivoSeleccion, setCultivoSeleccion] = useState(CULTIVO_NUEVO) // id de cultivo | CULTIVO_NUEVO
  const [cultivoForm, setCultivoForm] = useState(CULTIVO_NUEVO_VACIO)
  const [estadiosPorCultivo, setEstadiosPorCultivo] = useState({})

  // ── Alta de un lote sin salir del modal ───────────────────────────────
  const [creandoLote, setCreandoLote] = useState(false)
  const [lotesCreados, setLotesCreados] = useState([])
  const [nuevoLote, setNuevoLote] = useState({ nombre: '', tipo_suelo: '' })
  const [dibujandoLimite, setDibujandoLimite] = useState(false)
  const [poligonoNuevo, setPoligonoNuevo] = useState(null)
  const [areaNuevaM2, setAreaNuevaM2] = useState(null)
  const [autointerseccionNueva, setAutointerseccionNueva] = useState(false)
  const [guardandoLote, setGuardandoLote] = useState(false)
  const [errorLote, setErrorLote] = useState('')
  const loteAntesDeCrear = useRef('')
  const inputRef = useRef()

  // ── Carga desde imagen satelital (sin subir archivo) ──────────────────
  const [fechaDeseada, setFechaDeseada] = useState('')
  const [buscandoEscenas, setBuscandoEscenas] = useState(false)
  const [errorBusqueda, setErrorBusqueda] = useState('')
  const [escenas, setEscenas] = useState([])
  const [escenaSeleccionada, setEscenaSeleccionada] = useState(null)

  // Los lotes creados desde este modal se suman a los que llegan por props
  // hasta que el padre recarga su lista.
  const lotesTodos = [...(lotes ?? []), ...lotesCreados.filter((n) => !(lotes ?? []).some((l) => l.id === n.id))]
  const loteSeleccionado = lotesTodos.find((l) => l.id === loteId)
  const areaNuevaHa = areaNuevaM2 != null ? areaNuevaM2 / 10000 : null
  const areaNuevaFueraDeRango = areaNuevaHa != null && (areaNuevaHa < AREA_MIN_HA || areaNuevaHa > AREA_MAX_HA)
  const indiceInfo = INDICES.find((i) => i.value === indiceMostrado)
  const indicesParaSensor = indicesDisponibles(sensor)
  const cultivosLote = loteSeleccionado?.cultivos ?? []
  const creandoCultivo = cultivoSeleccion === CULTIVO_NUEVO
  const cultivoElegido = creandoCultivo ? null : cultivosLote.find((c) => c.id === cultivoSeleccion) ?? null
  // Un cultivo existente al que se le tocó algún dato: al continuar se actualiza el guardado.
  const cultivoModificado = Boolean(cultivoElegido) && (() => {
    const original = formDesdeCultivo(cultivoElegido)
    return Object.keys(original).some((k) => original[k] !== cultivoForm[k])
  })()
  const estadiosDisponibles = estadiosPorCultivo[cultivoForm.tipo_cultivo] ?? []
  const geotiffVisible = fuente === 'dron' ? limitesGeotiff : null
  // Si no se pudo leer la ubicación del archivo (CRS raro, sin georreferencia)
  // no se bloquea: el worker hace la validación completa.
  const geotiffFueraDelLote = Boolean(
    geotiffVisible && loteSeleccionado?.geometry && !geotiffCercaDelLote(geotiffVisible, loteSeleccionado.geometry)
  )
  const boundsMapa = useMemo(() => {
    const geoms = [loteSeleccionado?.geometry, geotiffVisible].filter(Boolean)
    if (geoms.length === 0) return null
    const todos = geoms.map((g) => boundsDesdePoligono(g.coordinates))
    return [
      [Math.min(...todos.map((b) => b[0][0])), Math.min(...todos.map((b) => b[0][1]))],
      [Math.max(...todos.map((b) => b[1][0])), Math.max(...todos.map((b) => b[1][1]))],
    ]
  }, [loteSeleccionado, geotiffVisible])

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
    listarEstadiosFenologicos().then(setEstadiosPorCultivo).catch(() => setEstadiosPorCultivo({}))
  }, [])

  useEffect(() => {
    // el estadio elegido pertenece a la escala del cultivo anterior: si cambia
    // el tipo y ya no está en la lista, se borra para no mandar uno inválido.
    if (estadioFenologico && estadiosDisponibles.length > 0 && !estadiosDisponibles.includes(estadioFenologico)) {
      setEstadioFenologico('')
    }
  }, [cultivoForm.tipo_cultivo, estadiosPorCultivo]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!archivo) { setLimitesGeotiff(null); return }
    let cancelado = false
    leerLimitesGeotiff(archivo).then((poligono) => { if (!cancelado) setLimitesGeotiff(poligono) })
    return () => { cancelado = true }
  }, [archivo])

  useEffect(() => {
    // al cambiar de lote se propone su cultivo más reciente (autocompleta los
    // campos); si no tiene ninguno, se arranca con un cultivo nuevo en blanco.
    const reciente = cultivoMasReciente(loteSeleccionado)
    setCultivoSeleccion(reciente?.id ?? CULTIVO_NUEVO)
    setCultivoForm(reciente ? formDesdeCultivo(reciente) : CULTIVO_NUEVO_VACIO)
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
    setSensor(fuente === 'satelite' ? 'sentinel2' : SENSOR_POR_DEFECTO)
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
    if (!loteId) return
    handleArchivo(e.dataTransfer.files[0])
  }

  function handleSiguiente() {
    if (!loteId) { setError('Seleccioná a qué lote pertenece este vuelo.'); return }
    if (fuente === 'dron' && !archivo) { setError('Seleccioná un archivo GeoTIFF.'); return }
    if (geotiffFueraDelLote) { setError(MSG_FUERA_DEL_LOTE); return }
    if (fuente === 'satelite' && !escenaSeleccionada) { setError('Elegí una escena satelital.'); return }
    if (fuente === 'satelite') setFechaVuelo(escenaSeleccionada.fecha)
    setError('')
    setStep('cultivo')
  }

  function abrirNuevoLote() {
    loteAntesDeCrear.current = loteId
    setLoteId('')
    setNuevoLote({ nombre: '', tipo_suelo: '' })
    setDibujandoLimite(false)
    setPoligonoNuevo(null)
    setAreaNuevaM2(null)
    setAutointerseccionNueva(false)
    setErrorLote('')
    setError('')
    setCreandoLote(true)
  }

  function cancelarNuevoLote() {
    setCreandoLote(false)
    setDibujandoLimite(false)
    setLoteId(loteAntesDeCrear.current)
    setErrorLote('')
  }

  function onDibujoNuevoLote(geojson, areaM2, autointerseccion) {
    setPoligonoNuevo(geojson)
    setAreaNuevaM2(areaM2)
    setAutointerseccionNueva(!!autointerseccion)
    setErrorLote('')
  }

  async function handleGuardarLote() {
    if (!nuevoLote.nombre.trim()) { setErrorLote('El nombre del lote es requerido.'); return }
    if (autointerseccionNueva) {
      setErrorLote('El polígono tiene lados que se cruzan entre sí — corregilo antes de guardar.')
      return
    }
    if (areaNuevaFueraDeRango) {
      setErrorLote(`El área del polígono (${areaNuevaHa.toFixed(2)} ha) está fuera del rango esperado (${AREA_MIN_HA}-${AREA_MAX_HA} ha).`)
      return
    }
    setGuardandoLote(true)
    setErrorLote('')
    try {
      const { data } = await client.post('/lotes', {
        nombre: nuevoLote.nombre.trim(),
        tipo_suelo: nuevoLote.tipo_suelo || null,
        geometry: poligonoNuevo,
      })
      setLotesCreados((prev) => [...prev, data])
      setLoteId(data.id)
      setCreandoLote(false)
      setDibujandoLimite(false)
      onLoteCreado?.()
    } catch (err) {
      const detail = err.response?.data?.detail
      setErrorLote(Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : detail || 'Error al crear el lote.')
    } finally {
      setGuardandoLote(false)
    }
  }

  function elegirCultivo(cultivo) {
    setCultivoSeleccion(cultivo.id)
    setCultivoForm(formDesdeCultivo(cultivo))
    setError('')
  }

  function nuevoCultivo() {
    setCultivoSeleccion(CULTIVO_NUEVO)
    setCultivoForm(CULTIVO_NUEVO_VACIO)
    setError('')
  }

  function handleContinuarCultivo() {
    if (!cultivoForm.tipo_cultivo) { setError('Elegí el tipo de cultivo.'); return }
    if (cultivoForm.fecha_siembra && cultivoForm.fecha_cosecha && cultivoForm.fecha_cosecha < cultivoForm.fecha_siembra) {
      setError('La fecha de cosecha no puede ser anterior a la de siembra.')
      return
    }
    if (!estadioFenologico.trim()) { setError('El estadio fenológico es obligatorio.'); return }
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

  function cultivoFormPayload() {
    return {
      tipo_cultivo: cultivoForm.tipo_cultivo,
      variedad: cultivoForm.variedad.trim() || null,
      fecha_siembra: cultivoForm.fecha_siembra ? new Date(cultivoForm.fecha_siembra).toISOString() : null,
      fecha_cosecha: cultivoForm.fecha_cosecha ? new Date(cultivoForm.fecha_cosecha).toISOString() : null,
    }
  }

  function setCampoCultivo(campo, valor) {
    setCultivoForm((prev) => ({ ...prev, [campo]: valor }))
  }

  async function handleSubmit() {
    setLoading(true)
    setError('')

    try {
      if (cultivoModificado) {
        await client.put(`/lotes/${loteId}/cultivos/${cultivoSeleccion}`, cultivoFormPayload())
      }

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
          indices.filter((i) => i !== 'ndvi'),
          cultivoSeleccion === CULTIVO_NUEVO
            ? { cultivo: cultivoFormPayload() }
            : { cultivo_id: cultivoSeleccion },
        )
      } else {
        const fd = new FormData()
        fd.append('archivo', archivo)
        fd.append('sensor', sensor)
        if (estadioFenologico.trim()) fd.append('estadio_fenologico', estadioFenologico.trim())
        if (fechaVuelo) fd.append('fecha_vuelo', new Date(fechaVuelo).toISOString())
        if (cultivoSeleccion === CULTIVO_NUEVO) {
          const nuevo = cultivoFormPayload()
          fd.append('cultivo_tipo', nuevo.tipo_cultivo)
          if (nuevo.variedad) fd.append('cultivo_variedad', nuevo.variedad)
          if (nuevo.fecha_siembra) fd.append('cultivo_fecha_siembra', nuevo.fecha_siembra)
          if (nuevo.fecha_cosecha) fd.append('cultivo_fecha_cosecha', nuevo.fecha_cosecha)
        } else {
          fd.append('cultivo_id', cultivoSeleccion)
        }

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
      // En satélite el archivo no existe todavía: el worker encola el batch al terminar la descarga.
      if (fuente !== 'satelite' && indicesAdicionales.length > 0) {
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
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">×</button>
        </div>

        {(
          <div className="wizard-stepper">
            {PASOS.map((paso, i) => {
              const indiceActual = PASOS.findIndex((p) => p.key === step)
              const estado = i === indiceActual ? ' wizard-step--active' : i < indiceActual ? ' wizard-step--done' : ''
              return (
                <Fragment key={paso.key}>
                  {i > 0 && <div className={`wizard-step-line${i <= indiceActual ? ' wizard-step-line--done' : ''}`} />}
                  <div className={`wizard-step${estado}`}>
                    <span className="wizard-step-icon">{i < indiceActual ? <IconCheck /> : paso.icon}</span>
                    <span className="wizard-step-label">{paso.label}</span>
                  </div>
                </Fragment>
              )
            })}
          </div>
        )}

        {(
        <div className="wizard-split">
        <div className="wizard-split-datos">
        {step === 'carga' && creandoLote ? (
          <div className="modal-form">
            <p className="config-analisis-titulo">Nuevo lote</p>

            <div className="form-group">
              <label htmlFor="nl_nombre">Nombre del lote</label>
              <input
                id="nl_nombre"
                type="text"
                placeholder="Ej: Lote Norte — Parcela 3"
                value={nuevoLote.nombre}
                onChange={(e) => setNuevoLote((f) => ({ ...f, nombre: e.target.value }))}
                disabled={guardandoLote}
                autoFocus
              />
            </div>

            <div className="form-group">
              <label htmlFor="nl_suelo">Tipo de suelo <span className="label-opcional">(opcional)</span></label>
              <select
                id="nl_suelo"
                value={nuevoLote.tipo_suelo}
                onChange={(e) => setNuevoLote((f) => ({ ...f, tipo_suelo: e.target.value }))}
                disabled={guardandoLote}
              >
                {TIPOS_SUELO.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label>Límites</label>
              <div className="nuevo-lote-limite">
              <button
                type="button"
                className={`modo-limite-btn${dibujandoLimite ? ' modo-limite-btn--activo' : ''}`}
                onClick={() => setDibujandoLimite((d) => !d)}
                disabled={guardandoLote}
              >
                🗺️ Dibujar en mapa
              </button>
              <span className="nuevo-lote-o">O al cargar un GeoTIFF se determinarán los límites</span>
              </div>
            </div>

            {areaNuevaHa != null && (
              <p className={`area-badge${areaNuevaFueraDeRango ? ' area-badge--alerta' : ''}`}>
                Área del polígono: {areaNuevaHa.toFixed(2)} ha
                {areaNuevaFueraDeRango && ' — fuera del rango esperado para un lote agrícola'}
              </p>
            )}
            {autointerseccionNueva && (
              <p className="area-badge area-badge--alerta">
                ⚠️ El polígono tiene lados que se cruzan entre sí — corregilo antes de guardar.
              </p>
            )}

            {errorLote && <p className="error-message">{errorLote}</p>}

            <div className="modal-actions modal-actions--wizard">
              <button type="button" className="btn-secondary" onClick={cancelarNuevoLote} disabled={guardandoLote}>
                Cancelar
              </button>
              <button type="button" className="btn-primary" onClick={handleGuardarLote} disabled={guardandoLote}>
                {guardandoLote ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        ) : step === 'carga' ? (
          <div className={`modal-form${loteId ? '' : ' modal-form--sin-lote'}`}>
            <div className="form-group">
              <label htmlFor="lote">Lote</label>
              <div className="lote-selector-fila">
                <select
                  id="lote"
                  value={loteId}
                  onChange={(e) => setLoteId(e.target.value)}
                  disabled={loading}
                >
                  <option value="" disabled>Seleccioná un lote…</option>
                  {lotesTodos.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.nombre}{cultivoMasReciente(l) ? ` — ${etiquetaTipoCultivo(cultivoMasReciente(l).tipo_cultivo)}` : ''}
                    </option>
                  ))}
                </select>
                <button type="button" className="btn-nuevo-lote" onClick={abrirNuevoLote} disabled={loading}>
                  ＋ Nuevo lote
                </button>
              </div>
            </div>

            <div className="modo-limite-toggle">
              <button
                type="button"
                className={`modo-limite-btn${fuente === 'dron' ? ' modo-limite-btn--activo' : ''}`}
                onClick={() => cambiarFuente('dron')}
                disabled={loading || !loteId}
              >
                <IconDron size={18} /> Subir archivo (dron)
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
                    disabled={loading || !loteId}
                  >
                    {SENSORES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>

                {geotiffFueraDelLote && (
                  <div className="requisitos-box requisitos-box--error">
                    <IconInfo />
                    <p>
                      <strong>{MSG_FUERA_DEL_LOTE}</strong><br />
                      El área naranja del mapa es la que cubre el archivo. Verificá que elegiste el lote correcto o
                      que el GeoTIFF corresponde a este campo.
                    </p>
                  </div>
                )}

                {inspeccion && !inspeccion.compatible && (
                  <div className="requisitos-box requisitos-box--error">
                    <IconInfo />
                    <p>
                      <strong>El archivo no coincide con el sensor seleccionado</strong><br />
                      {inspeccion.mensaje}
                    </p>
                  </div>
                )}

                <div
                  className={`dropzone${dragging ? ' dropzone--activo' : ''}${archivo ? ' dropzone--ok' : ''}`}
                  onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => { if (loteId) inputRef.current.click() }}
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
                disabled={fuente === 'dron' ? !archivo || geotiffFueraDelLote : !escenaSeleccionada}
              >
                Siguiente
                <FlechaAdelante />
              </button>
            </div>
          </div>
        ) : step === 'cultivo' ? (
          <div className="modal-form">
            <p className="config-analisis-titulo">Información de cultivo</p>

            <CultivoDropdown
              cultivos={cultivosLote}
              seleccion={cultivoSeleccion}
              creando={creandoCultivo}
              onElegir={elegirCultivo}
              onNuevo={nuevoCultivo}
              disabled={loading}
            />

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="cultivo_tipo">Tipo de cultivo</label>
                <select
                  id="cultivo_tipo"
                  value={cultivoForm.tipo_cultivo}
                  onChange={(e) => setCampoCultivo('tipo_cultivo', e.target.value)}
                  disabled={loading}
                >
                  <option value="" disabled>Seleccionar...</option>
                  {CULTIVOS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
              <div className="form-group">
                <div className="label-con-ayuda">
                  <label htmlFor="cultivo_variedad">Variedad</label>
                  <AyudaVariedad />
                </div>
                <input
                  id="cultivo_variedad"
                  type="text"
                  placeholder="Ej: DM 46i17"
                  maxLength={100}
                  value={cultivoForm.variedad}
                  onChange={(e) => setCampoCultivo('variedad', e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="cultivo_siembra">Fecha de siembra</label>
                <input
                  id="cultivo_siembra"
                  type="date"
                  value={cultivoForm.fecha_siembra}
                  onChange={(e) => setCampoCultivo('fecha_siembra', e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="form-group">
                <label htmlFor="cultivo_cosecha">Fecha de cosecha</label>
                <input
                  id="cultivo_cosecha"
                  type="date"
                  value={cultivoForm.fecha_cosecha}
                  min={cultivoForm.fecha_siembra || undefined}
                  onChange={(e) => setCampoCultivo('fecha_cosecha', e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {cultivoModificado && (
              <div className="requisitos-box requisitos-box--aviso">
                <IconInfo />
                <p>
                  <strong>Modificaste los datos de este cultivo.</strong><br />
                  Al continuar se va a actualizar el cultivo guardado, y el cambio también se ve en sus análisis anteriores.
                  Si querés registrar otro cultivo distinto, usá "＋ Nuevo cultivo".
                </p>
              </div>
            )}

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="fecha_vuelo">Fecha del vuelo</label>
                <input
                  id="fecha_vuelo"
                  type="date"
                  value={fechaVuelo}
                  onChange={(e) => setFechaVuelo(e.target.value)}
                  disabled={loading || fuente === 'satelite'}
                  title={fuente === 'satelite' ? 'Es la fecha real de captura de la escena elegida — no se puede editar.' : undefined}
                />
              </div>
              <div className="form-group">
                <label htmlFor="estadio_vuelo">Estadio fenológico</label>
                <select
                  id="estadio_vuelo"
                  value={estadioFenologico}
                  onChange={(e) => setEstadioFenologico(e.target.value)}
                  disabled={loading || !cultivoForm.tipo_cultivo}
                  required
                >
                  <option value="" disabled>
                    {cultivoForm.tipo_cultivo ? 'Seleccionar...' : 'Elegí primero el tipo de cultivo'}
                  </option>
                  {estadiosDisponibles.map((e) => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
            </div>

            {error && <p className="error-message">{error}</p>}

            <div className="modal-actions modal-actions--wizard">
              <button type="button" className="btn-secondary" onClick={() => { setError(''); setStep('carga') }}>
                <FlechaAtras />
                Atrás
              </button>
              <button type="button" className="btn-primary" onClick={handleContinuarCultivo}>
                Continuar
                <FlechaAdelante />
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
                  <span><strong>Cultivo:</strong> {descripcionCultivo({ ...cultivoForm, variedad: cultivoForm.variedad.trim() || null, fecha_siembra: cultivoForm.fecha_siembra ? `${cultivoForm.fecha_siembra}T00:00:00Z` : null })}</span>
                  <span><strong>Estadio:</strong> {estadioFenologico.trim()}</span>
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
              <p className="config-analisis-sub">
                Elegí qué índices calcular. NDVI se calcula siempre (es la base del diagnóstico); destildá los demás que no necesites.
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
              <button type="button" className="btn-secondary" onClick={() => setStep('cultivo')} disabled={loading}>
                <FlechaAtras />
                Atrás
              </button>
              <button type="button" className="btn-primary" onClick={handleSubmit} disabled={loading}>
                {loading ? 'Subiendo...' : <>Iniciar Análisis <FlechaAdelante /></>}
              </button>
            </div>
          </div>
        )}
        </div>

        <aside className="wizard-split-mapa">
          {creandoLote && dibujandoLimite ? (
            <MapaDibujoLote key="dibujo-nuevo-lote" onChange={onDibujoNuevoLote} initialGeoJSON={poligonoNuevo} height="100%" />
          ) : boundsMapa ? (
            <>
            <MapContainer
              key={loteId}
              bounds={boundsMapa}
              style={{ height: '100%', width: '100%' }}
              scrollWheelZoom={false}
            >
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attribution="Tiles &copy; Esri"
              />
              {loteSeleccionado?.geometry && (
                <GeoJSON
                  key={`lote-${loteId}`}
                  data={loteSeleccionado.geometry}
                  style={{ color: '#2ecc71', weight: 2, fillOpacity: 0.15 }}
                />
              )}
              {geotiffVisible && (
                <GeoJSON
                  key={`tif-${archivo?.name}-${archivo?.size}`}
                  data={geotiffVisible}
                  style={{ color: '#f59e0b', weight: 2, dashArray: '6 4', fillOpacity: 0.08 }}
                />
              )}
              <FitBounds bounds={boundsMapa} />
            </MapContainer>
            <div className="wizard-mapa-leyenda">
              {loteSeleccionado?.geometry && <span><i style={{ background: '#2ecc71' }} />Límite del lote</span>}
              {geotiffVisible && <span><i style={{ background: '#f59e0b' }} />Área del GeoTIFF</span>}
            </div>
            </>
          ) : (
            <MapaNEA
              aviso={
                creandoLote
                  ? null
                  : loteSeleccionado
                    ? 'Este lote no tiene límite cargado todavía.'
                    : 'Seleccioná un lote para ver sus límites.'
              }
            />
          )}
        </aside>
        </div>
        )}
      </div>
    </div>
  )
}
