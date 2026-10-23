import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useVueloProgreso } from '../hooks/useVueloProgreso'
import client from '../api/client'
import { eliminarVuelo, listarIndicesVuelo, reintentarVuelo } from '../api/analisis'
import { descargarReportePdf, exportarZonas } from '../api/reportes'
import { extraerMensajeErrorBlob } from '../utils/descargarArchivo'
import BarraProgreso from '../components/BarraProgreso'
import MapaIndice from '../components/MapaIndice'
import MapaCapas from '../components/MapaCapas'
import { cultivoMasReciente, etiquetaTipoCultivo } from '../utils/cultivos'
import ModalCargaGeoTIFF from '../components/ModalCargaGeoTIFF'
import ModalNuevoLote from '../components/ModalNuevoLote'
import ModalLimites from '../components/ModalLimites'
import ModalConfirmarEliminar from '../components/ModalConfirmarEliminar'
import ModalElegirLote from '../components/ModalElegirLote'
import ModalPreviewPdf from '../components/ModalPreviewPdf'
import SidebarNav from '../components/SidebarNav'
import TopbarPanel from '../components/TopbarPanel'

/* ──────── Icons ──────── */
const IconLotes = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
    <line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
  </svg>
)
const IconDiagnostico = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
  </svg>
)
const IconInformes = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
    <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
  </svg>
)
const IconConfig = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
  </svg>
)
const IconArrow = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
  </svg>
)
const IconZoom = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
)
const IconMap = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
    <line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
  </svg>
)
const IconTrash = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
  </svg>
)
const IconDescargar = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
    <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
)
const IconRetry = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="1 4 1 10 7 10"/>
    <path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>
  </svg>
)
const IconExpandir = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 3 21 3 21 9"/>
    <polyline points="9 21 3 21 3 15"/>
    <line x1="21" y1="3" x2="14" y2="10"/>
    <line x1="3" y1="21" x2="10" y2="14"/>
  </svg>
)
const IconContraer = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="4 14 10 14 10 20"/>
    <polyline points="20 10 14 10 14 4"/>
    <line x1="14" y1="10" x2="21" y2="3"/>
    <line x1="3" y1="21" x2="10" y2="14"/>
  </svg>
)

/* ──────── Helpers ──────── */

const ESTADO_BADGE = {
  completado: { label: 'Completado', cls: 'badge-optimo' },
  procesando: { label: 'Procesando', cls: 'badge-procesando' },
  pendiente:  { label: 'Pendiente',  cls: 'badge-procesando' },
  error:      { label: 'Error',      cls: 'badge-critico' },
}

function fmtFecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })
}

// fecha_vuelo se carga como fecha sin hora (medianoche UTC): en UTC para no
// mostrar el día anterior en Argentina.
function fmtFechaVuelo(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' })
}

function saludoSegunHora() {
  const h = new Date().getHours()
  if (h < 6) return 'Buenas noches'
  if (h < 13) return 'Buen día'
  if (h < 20) return 'Buenas tardes'
  return 'Buenas noches'
}

function fmtTiempoRelativo(fecha) {
  const diff = Date.now() - fecha.getTime()
  const mins = Math.floor(diff / 60000)
  const horas = Math.floor(diff / 3600000)
  const dias = Math.floor(diff / 86400000)
  if (mins < 1) return 'Justo ahora'
  if (mins < 60) return `Hace ${mins} min`
  if (horas < 24) return `Hace ${horas}h`
  if (dias === 1) return 'Ayer'
  if (dias < 7) return `Hace ${dias} días`
  return fmtFecha(fecha.toISOString())
}

function buildActivityFeed(loteRows, vueloRows, userName) {
  const items = []

  items.push({
    tipo: 'user',
    texto: `Sesión iniciada por ${userName}`,
    fecha: new Date(),
  })

  for (const lote of loteRows) {
    if (lote.created_at) {
      items.push({
        tipo: 'ok',
        texto: `Lote "${lote.nombre}" registrado`,
        fecha: new Date(lote.created_at),
      })
    }
  }

  for (const v of vueloRows) {
    const nombre = v.lote?.nombre || 'Lote'
    const fecha = new Date(v.created_at)
    if (v.estado === 'completado') {
      items.push({ tipo: 'ok', texto: `Análisis completado en ${nombre}`, fecha })
    } else if (v.estado === 'error') {
      items.push({ tipo: 'alerta', texto: `Error en análisis de ${nombre}`, fecha })
    } else if (v.estado === 'procesando') {
      items.push({ tipo: 'upload', texto: `Procesando análisis en ${nombre}`, fecha })
    } else {
      items.push({ tipo: 'upload', texto: `Ortomosaico cargado en ${nombre}`, fecha })
    }
  }

  items.sort((a, b) => b.fecha - a.fecha)
  return items.slice(0, 6)
}


/* ──────── KPI Card ──────── */
function KpiCard({ label, value, delta, deltaType, icon, highlight }) {
  return (
    <div className={`kpi-card${highlight ? ' kpi-card--highlight' : ''}`}>
      <div className="kpi-card-top">
        <span className="kpi-label">{label}</span>
        <span className="kpi-icon">{icon}</span>
      </div>
      <div className="kpi-value">{value}</div>
      {delta && <div className={`kpi-delta kpi-delta--${deltaType ?? 'up'}`}>{delta}</div>}
    </div>
  )
}

function KpiFranja({ items }) {
  return (
    <div className="kpi-franja">
      {items.map(it => (
        <div key={it.etiqueta} className="kpi-franja-item">
          <span className="kpi-franja-etiqueta">{it.etiqueta}</span>
          <div className="kpi-franja-valor">
            {it.valor}
            {it.unidad && <span className="kpi-franja-unidad">{it.unidad}</span>}
          </div>
          <span className={`kpi-franja-nota kpi-franja-nota--${it.tono}`}>{it.nota}</span>
        </div>
      ))}
    </div>
  )
}

/* ──────── Mapa de análisis (panel inferior) ──────── */
const INDICE_LABEL = { ndvi: 'NDVI', ndre: 'NDRE', savi: 'SAVI', gndvi: 'GNDVI', exg: 'ExG' }

// Debe coincidir con workers/gis/zonas.py::AREA_MINIMA_M2 — el pipeline
// descarta cualquier fragmento vectorizado más chico que esto (evita ruido
// de píxeles sueltos), así que un lote entero por debajo de este umbral
// nunca puede generar una zona, sin importar cuán distinto sea su índice.
const AREA_MINIMA_ZONA_HA = 1

function AnalisisMap({ loteId, vueloId, indice, limite, loteAreaHa, onCompletado }) {
  // mapa de vistazo: los huecos chicos se rellenan con la zona vecina
  const { estado, geojson, errorMsg } = useVueloProgreso(loteId, vueloId, indice, { absorber: true })

  // Un lote sin límite lo recibe del worker al procesar el GeoTIFF: al terminar
  // hay que recargar los lotes para que aparezcan el límite y la superficie.
  const completado = estado?.estado === 'completado'
  useEffect(() => {
    if (completado) onCompletado?.()
  }, [completado]) // eslint-disable-line react-hooks/exhaustive-deps

  // errorMsg puede llegar sin que `estado` se haya resuelto nunca (falla la
  // primera consulta de estado, ej. 404) — antes `!estado` cortaba acá y se
  // quedaba en "Cargando análisis..." para siempre, tapando el error.
  if (!estado && !errorMsg) return <p className="estado-msg" style={{ padding: '1rem' }}>Cargando análisis...</p>
  if (!estado) {
    return <p className="estado-msg" style={{ padding: '1rem', color: '#b91c1c' }}>{errorMsg}</p>
  }

  const estadoActual = estado.estado
  if (estadoActual === 'completado' && geojson) {
    const nFeatures = geojson.features?.length ?? 0
    if (nFeatures === 0) {
      const loteChico = loteAreaHa != null && loteAreaHa < AREA_MINIMA_ZONA_HA
      return (
        <div className="estado-msg" style={{ padding: '1rem 1.25rem' }}>
          <strong>No se generaron zonas para marcar en el mapa.</strong>
          <p style={{ marginTop: '0.5rem', color: '#6b7280', lineHeight: 1.5 }}>
            {loteChico ? (
              <>
                Tu lote mide <strong>{loteAreaHa.toFixed(2)} ha</strong>, por debajo del área mínima de
                zonificación (<strong>{AREA_MINIMA_ZONA_HA} ha</strong>). El sistema descarta por diseño
                cualquier zona más chica que ese umbral, para no marcar ruido de píxeles sueltos — como el
                lote completo es más chico que el umbral, ninguna zona puede superarlo nunca, sin importar
                el resultado del índice. <strong>Solución:</strong> usá esto solo para probar la carga, no
                para ver zonificación real — para eso hace falta un lote de al menos {AREA_MINIMA_ZONA_HA}–2 ha.
              </>
            ) : (
              <>
                El índice {INDICE_LABEL[indice] ?? indice.toUpperCase()} se mantuvo uniforme y dentro de rango
                normal en toda la escena — no se encontraron zonas de estrés, suelo desnudo ni vigor excesivo
                que superen el área mínima de zonificación ({AREA_MINIMA_ZONA_HA} ha). Esto normalmente indica
                un lote homogéneo y sano para esta fecha, no un error. <strong>Si esperabas ver variación:</strong>{' '}
                probá otra fecha/escena, o analizá otro índice como NDRE (más sensible a estrés temprano) con
                el selector de índices de arriba.
              </>
            )}
          </p>
        </div>
      )
    }
    return <MapaIndice geojson={geojson} indice={indice} limite={limite} />
  }
  if (estadoActual === 'error' || errorMsg) {
    return (
      <p className="estado-msg" style={{ padding: '1rem', color: '#b91c1c' }}>
        {errorMsg || estado?.error || 'Error en el procesamiento.'}
      </p>
    )
  }
  // El análisis ya terminó (estado='completado') pero el GeoJSON resumido
  // (absorber=true) todavía no llegó — es una vista derivada que se genera
  // en el momento, no una re-ejecución del análisis, así que no corresponde
  // mostrar la barra de progreso del procesamiento original.
  if (estadoActual === 'completado' && !geojson) {
    return (
      <div className="diagnostico-loading">
        <span className="diagnostico-spinner" />
        <p>Generando vista del mapa...</p>
      </div>
    )
  }
  return (
    <div style={{ padding: '1rem' }}>
      <BarraProgreso progreso={estado?.progreso ?? 0} mensaje={estado?.mensaje} estado={estadoActual} />
    </div>
  )
}

/* ──────── Dashboard ──────── */
export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [loteRows, setLoteRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [showModalNuevoLote, setShowModalNuevoLote] = useState(false)
  const [showModalElegirLote, setShowModalElegirLote] = useState(false)
  const [loteParaLimites, setLoteParaLimites] = useState(null)
  const [analisisParaEliminar, setAnalisisParaEliminar] = useState(null)
  const [reintentandoId, setReintentandoId] = useState(null)
  const [descargando, setDescargando] = useState(null) // `${vueloId}:pdf|geojson|shapefile`
  const [exportMenuAbierto, setExportMenuAbierto] = useState(null) // vueloId con el menú de exportar abierto
  const exportMenuRef = useRef(null)
  const [previewPdf, setPreviewPdf] = useState(null) // { titulo, blob, filename } | null
  const [tablaError, setTablaError] = useState('')
  const [selectedVuelo, setSelectedVuelo] = useState(null)
  const [indicesDisponibles, setIndicesDisponibles] = useState([])
  const [mapaExpandido, setMapaExpandido] = useState(false)
  const [modoComparacion, setModoComparacion] = useState(false)
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 4

  useEffect(() => {
    if (!mapaExpandido) return
    function onKeyDown(e) {
      if (e.key === 'Escape') setMapaExpandido(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [mapaExpandido])

  useEffect(() => {
    if (!exportMenuAbierto) return
    function onClickFuera(e) {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target)) {
        setExportMenuAbierto(null)
      }
    }
    document.addEventListener('mousedown', onClickFuera)
    return () => document.removeEventListener('mousedown', onClickFuera)
  }, [exportMenuAbierto])

  const cargarDatos = useCallback(async ({ silencioso = false } = {}) => {
    if (!silencioso) setLoading(true)
    try {
      const { data } = await client.get('/lotes')
      const lotes = data.items ?? []
      const results = await Promise.allSettled(
        lotes.map(l => client.get(`/lotes/${l.id}/vuelos`))
      )
      setLoteRows(lotes.map((l, i) => ({
        ...l,
        vuelos: results[i].status === 'fulfilled' ? (results[i].value.data ?? []) : [],
      })))
    } catch {
      if (!silencioso) setLoteRows([])
    } finally {
      if (!silencioso) setLoading(false)
    }
  }, [])

  useEffect(() => { cargarDatos() }, [cargarDatos])

  useEffect(() => {
    if (!selectedVuelo) { setIndicesDisponibles([]); return }
    let cancelado = false
    listarIndicesVuelo(selectedVuelo.loteId, selectedVuelo.vueloId)
      .then((data) => { if (!cancelado) setIndicesDisponibles(data) })
      .catch(() => { if (!cancelado) setIndicesDisponibles([]) })
    return () => { cancelado = true }
  }, [selectedVuelo?.loteId, selectedVuelo?.vueloId])

  // Precarga el índice preferido del usuario (HU-R4-12) una vez que se sabe
  // qué índices están disponibles para este vuelo en particular — evita
  // mostrar una pastilla activa para un índice que no se calculó.
  useEffect(() => {
    if (!user?.indice_preferido) return
    const disponible = indicesDisponibles.find(
      (i) => i.indice === user.indice_preferido && i.estado === 'completado'
    )
    if (disponible) cambiarIndice(user.indice_preferido)
  }, [indicesDisponibles]) // eslint-disable-line react-hooks/exhaustive-deps

  function cambiarIndice(indice) {
    setSelectedVuelo((prev) => prev && { ...prev, indice })
  }

  function handleCargaExitosa(data) {
    setShowModal(false)
    cargarDatos()
    setSelectedVuelo({ loteId: data.lote_id, vueloId: data.vuelo_id, indice: 'ndvi' })
  }

  function handleNuevoLoteExitoso() {
    setShowModalNuevoLote(false)
    cargarDatos()
  }

  function handleVerDiagnosticos() {
    // con un solo lote no tiene sentido preguntar — vamos directo a sus vuelos
    if (loteRows.length === 1) {
      navigate(`/lotes/${loteRows[0].id}`)
      return
    }
    setShowModalElegirLote(true)
  }

  async function handleEliminarAnalisis() {
    const { loteId, vueloId } = analisisParaEliminar
    await eliminarVuelo(loteId, vueloId)
    setAnalisisParaEliminar(null)
    if (selectedVuelo?.vueloId === vueloId) { setSelectedVuelo(null); setModoComparacion(false) }
    cargarDatos()
  }

  async function handleReintentar(v) {
    setTablaError('')
    setReintentandoId(v.vueloId)
    try {
      await reintentarVuelo(v.lote.id, v.vueloId)
      await cargarDatos()
      setSelectedVuelo({ loteId: v.lote.id, vueloId: v.vueloId, indice: 'ndvi' })
    } catch (err) {
      setTablaError(err.response?.data?.detail || 'Error al reintentar el análisis.')
    } finally {
      setReintentandoId(null)
    }
  }

  async function handleDescargarReporte(v) {
    const key = `${v.vueloId}:pdf`
    setTablaError('')
    setDescargando(key)
    try {
      const blob = await descargarReportePdf(v.lote.id, v.vueloId)
      setPreviewPdf({
        titulo: `Reporte ejecutivo — ${v.lote.nombre}`,
        blob,
        filename: `reporte_ejecutivo_${v.vueloId}.pdf`,
      })
    } catch (err) {
      setTablaError(await extraerMensajeErrorBlob(err, 'No se pudo generar el reporte PDF.'))
    } finally {
      setDescargando(null)
    }
  }

  async function handleExportarZonas(v, formato) {
    const key = `${v.vueloId}:${formato}`
    setTablaError('')
    setDescargando(key)
    try {
      const { url } = await exportarZonas(v.lote.id, v.vueloId, formato)
      window.open(url, '_blank')
    } catch (err) {
      setTablaError(err.response?.data?.detail || `No se pudo exportar en formato ${formato}.`)
    } finally {
      setDescargando(null)
    }
  }

  const vueloRows = loteRows
    .flatMap(l => l.vuelos.map(v => ({ ...v, vueloId: v.vuelo_id ?? v.id, lote: l })))
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  const totalPages = Math.max(1, Math.ceil(vueloRows.length / PAGE_SIZE))
  const pageRows    = vueloRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const selectedVueloRow = vueloRows.find(v => v.vueloId === selectedVuelo?.vueloId)

  // Vuelos completados del mismo lote que el vuelo seleccionado actualmente
  const vuelosLoteActivo = selectedVuelo
    ? vueloRows.filter(v => v.lote.id === selectedVuelo.loteId && v.estado === 'completado')
    : []
  const puedeComparar = vuelosLoteActivo.length >= 2

  // La tabla "Análisis Recientes" solo se refrescaba cuando el usuario hacía una
  // acción (subir vuelo, eliminar, etc.) — sin este polling se quedaba mostrando
  // "Pendiente"/"Procesando" para siempre aunque el worker ya hubiera terminado,
  // porque nada más volvía a pedir /lotes. Silencioso para no tapar la tabla con
  // "Cargando..." cada 3s (mismo patrón de polling que DetalleLote.jsx).
  useEffect(() => {
    const hayActivos = vueloRows.some(v => v.estado === 'pendiente' || v.estado === 'procesando')
    if (!hayActivos) return
    const id = setInterval(() => cargarDatos({ silencioso: true }), 3000)
    return () => clearInterval(id)
  }, [vueloRows, cargarDatos])

  const vuelosCompletados = vueloRows.filter(v => v.estado === 'completado').length
  const vuelosEnProceso = vueloRows.filter(v => v.estado === 'pendiente' || v.estado === 'procesando').length
  const areaTotalHa = loteRows.reduce((suma, l) => suma + (l.area_ha || 0), 0)
  const lotesConLimite = loteRows.filter(l => l.area_ha > 0).length

  return (
    <div className="dashboard dashboard--resumen">
      {showModal && (
        <ModalCargaGeoTIFF
          lotes={loteRows}
          loteIdInicial={selectedVuelo?.loteId ?? null}
          onSuccess={handleCargaExitosa}
          onLoteCreado={cargarDatos}
          onClose={() => setShowModal(false)}
        />
      )}
      {showModalNuevoLote && (
        <ModalNuevoLote onSuccess={handleNuevoLoteExitoso} onClose={() => setShowModalNuevoLote(false)} />
      )}
      {loteParaLimites && (
        <ModalLimites
          lote={loteParaLimites}
          onSuccess={() => { setLoteParaLimites(null); cargarDatos() }}
          onClose={() => setLoteParaLimites(null)}
        />
      )}
      {analisisParaEliminar && (
        <ModalConfirmarEliminar
          titulo="Eliminar diagnóstico"
          mensaje={`¿Seguro que querés eliminar el vuelo de "${analisisParaEliminar.etiqueta}"? Esta acción no se puede deshacer.`}
          onConfirmar={handleEliminarAnalisis}
          onClose={() => setAnalisisParaEliminar(null)}
        />
      )}
      {showModalElegirLote && (
        <ModalElegirLote
          lotes={loteRows}
          onElegir={(loteId) => { setShowModalElegirLote(false); navigate(`/lotes/${loteId}`) }}
          onClose={() => setShowModalElegirLote(false)}
        />
      )}
      {previewPdf && (
        <ModalPreviewPdf
          titulo={previewPdf.titulo}
          blob={previewPdf.blob}
          filename={previewPdf.filename}
          onClose={() => setPreviewPdf(null)}
        />
      )}

      <SidebarNav user={user} onVerDiagnosticos={handleVerDiagnosticos} />

      <div className="dashboard-body">
        {/* Topbar */}
        <TopbarPanel migas={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Resumen' }]} />

        <main className="dashboard-main">
          {/* Portada */}
          <section className="hero-panel">
            <h1 className="hero-panel-titulo">
              {saludoSegunHora()}, {user?.nombre?.split(' ')[0] ?? 'Usuario'}
            </h1>
            <div className="hero-panel-acciones">
              <button type="button" className="hero-btn hero-btn--principal" onClick={() => setShowModal(true)}>
                Cargar nuevo análisis <IconArrow />
              </button>
              <button type="button" className="hero-btn" onClick={() => setShowModalNuevoLote(true)}>
                Nuevo lote
              </button>
              <button
                type="button"
                className="hero-btn"
                disabled={!vueloRows.some(v => v.estado === 'completado')}
                onClick={handleVerDiagnosticos}
              >
                Ver diagnósticos
              </button>
            </div>
          </section>

          {/* KPI cards */}
          <div className="kpi-row">
            <KpiCard
              label="LOTES REGISTRADOS"
              value={loteRows.length || '—'}
              delta={loteRows.length > 0 ? `${loteRows.length} activo${loteRows.length !== 1 ? 's' : ''}` : null}
              deltaType="up"
              icon={<IconLotes />}
            />
            <KpiCard
              label="ANÁLISIS REALIZADOS"
              value={vueloRows.length || '—'}
              delta={vuelosCompletados > 0 ? `${vuelosCompletados} completados` : null}
              deltaType="up"
              icon={<IconDiagnostico />}
            />
            <KpiCard
              label="ANÁLISIS COMPLETADOS"
              value={vuelosCompletados || '—'}
              delta={vuelosCompletados > 0 ? 'Con diagnóstico disponible' : 'Sin análisis aún'}
              deltaType={vuelosCompletados > 0 ? 'up' : 'neutral'}
              icon={<IconInformes />}
            />
            <KpiCard
              label="ÁREA MONITOREADA"
              value={areaTotalHa > 0 ? `${Math.round(areaTotalHa).toLocaleString('es-AR')}` : '—'}
              delta={areaTotalHa > 0 ? 'hectáreas totales' : 'Registrá un lote para comenzar'}
              deltaType={areaTotalHa > 0 ? 'up' : 'neutral'}
              icon={<IconConfig />}
              highlight={areaTotalHa > 0}
            />
          </div>


          {/* Grid principal */}
          <div className="dashboard-grid">
            {/* Columna izquierda */}
            <div className="dashboard-col-main">
              {/* Tabla análisis recientes */}
              <div className="card">
                <div className="card-header">
                  <div>
                    <h2 className="card-title">Análisis Recientes</h2>
                    <p className="card-sub">Últimos vuelos procesados y estado de vigor</p>
                  </div>
                  <button className="card-link" onClick={() => navigate('/lotes')}>Ver todos <IconArrow /></button>
                </div>
                {tablaError && (
                  <div className="error-message" style={{ margin: '0 1.1rem 0.75rem' }}>{tablaError}</div>
                )}
                <div className="card-body" style={{ padding: '0' }}>
                  {loading ? (
                    <p className="estado-msg" style={{ padding: '1rem 1.1rem' }}>Cargando...</p>
                  ) : loteRows.length === 0 ? (
                    <div className="empty-state">
                      <p>No hay lotes registrados.</p>
                      <p className="empty-hint">Creá un lote para comenzar.</p>
                    </div>
                  ) : vueloRows.length === 0 ? (
                    <div className="empty-state">
                      <p>No hay vuelos cargados todavía.</p>
                      <p className="empty-hint">Usá "Cargar Nuevo Análisis" para subir el primer vuelo de un lote.</p>
                    </div>
                  ) : (
                    <>
                      <table className="analisis-table">
                        <thead>
                          <tr>
                            <th>LOTE</th>
                            <th>FECHA DE VUELO</th>
                            <th>ESTADIO</th>
                            <th>ÍNDICES</th>
                            <th>ESTADO</th>
                            <th>ACCIÓN</th>
                          </tr>
                        </thead>
                        <tbody>
                          {pageRows.map(v => {
                            const badge = ESTADO_BADGE[v.estado] ?? { label: v.estado, cls: 'badge-procesando' }
                            return (
                              <tr key={v.vueloId} className={selectedVuelo?.vueloId === v.vueloId ? 'tr--active' : ''}>
                                <td>
                                  <div className="td-lote-nombre">{v.lote.nombre}</div>
                                  <div className="td-lote-info">
                                    {etiquetaTipoCultivo(v.cultivo?.tipo_cultivo ?? cultivoMasReciente(v.lote)?.tipo_cultivo) || 'Sin cultivo'}
                                    {v.lote.area_ha ? ` · ${Math.round(v.lote.area_ha)} ha` : ''}
                                  </div>
                                </td>
                                <td className="td-fecha">
                                  <div>{fmtFechaVuelo(v.fecha_vuelo)}</div>
                                  <div className="td-fecha-subido" title="Fecha en que se cargó el ortomosaico">
                                    Subido {fmtFecha(v.created_at)}
                                  </div>
                                </td>
                                <td>
                                  {v.estadio_fenologico
                                    ? <span className="vuelo-estadio-tag">{v.estadio_fenologico}</span>
                                    : <span className="td-vacio">—</span>}
                                </td>
                                <td>
                                  {v.indices && v.indices.length > 0 ? (
                                    <div className="td-indices-chips">
                                      {v.indices.map((ix) => {
                                        const ib = ESTADO_BADGE[ix.estado] ?? { label: ix.estado, cls: 'badge-procesando' }
                                        return (
                                          <span
                                            key={ix.indice}
                                            className={`indice-chip ${ib.cls}`}
                                            title={`${ix.indice.toUpperCase()} — ${ib.label}`}
                                          >
                                            {ix.indice.toUpperCase()}
                                          </span>
                                        )
                                      })}
                                    </div>
                                  ) : <span className="td-vacio">—</span>}
                                </td>
                                <td>
                                  <span className={`table-badge ${badge.cls}`}>{badge.label}</span>
                                </td>
                                <td>
                                  <div className="td-acciones">
                                    <button
                                      className="tbl-btn"
                                      title="Ver análisis"
                                      onClick={() => setSelectedVuelo({ loteId: v.lote.id, vueloId: v.vueloId, indice: 'ndvi' })}
                                    >
                                      <IconZoom />
                                    </button>
                                    {v.estado === 'completado' && (
                                      <button
                                        className="tbl-btn"
                                        title="Ver diagnóstico"
                                        onClick={() => navigate(`/lotes/${v.lote.id}/vuelos/${v.vueloId}`)}
                                      >
                                        <IconDiagnostico />
                                      </button>
                                    )}
                                    {v.estado === 'completado' && (
                                      <>
                                        <button
                                          className="tbl-btn"
                                          title="Descargar reporte PDF"
                                          disabled={descargando === `${v.vueloId}:pdf`}
                                          onClick={() => handleDescargarReporte(v)}
                                        >
                                          <IconInformes />
                                        </button>
                                        <div
                                          className="export-zonas-wrap"
                                          ref={exportMenuAbierto === v.vueloId ? exportMenuRef : null}
                                        >
                                          <button
                                            className="tbl-btn"
                                            title="Exportar zonas"
                                            onClick={() => setExportMenuAbierto(
                                              (cur) => cur === v.vueloId ? null : v.vueloId
                                            )}
                                          >
                                            <IconDescargar />
                                          </button>
                                          {exportMenuAbierto === v.vueloId && (
                                            <div className="export-zonas-popover">
                                              <button
                                                type="button"
                                                disabled={descargando === `${v.vueloId}:geojson`}
                                                onClick={() => {
                                                  setExportMenuAbierto(null)
                                                  handleExportarZonas(v, 'geojson')
                                                }}
                                              >
                                                GeoJSON
                                              </button>
                                              <button
                                                type="button"
                                                disabled={descargando === `${v.vueloId}:shapefile`}
                                                onClick={() => {
                                                  setExportMenuAbierto(null)
                                                  handleExportarZonas(v, 'shapefile')
                                                }}
                                              >
                                                Shapefile
                                              </button>
                                            </div>
                                          )}
                                        </div>
                                      </>
                                    )}
                                    <button
                                      className="tbl-btn"
                                      title="Límites"
                                      onClick={() => setLoteParaLimites(v.lote)}
                                    >
                                      <IconMap />
                                    </button>
                                    {v.estado === 'error' && (
                                      <button
                                        className="tbl-btn tbl-btn--retry"
                                        title="Reintentar análisis"
                                        disabled={reintentandoId === v.vueloId}
                                        onClick={() => handleReintentar(v)}
                                      >
                                        <IconRetry />
                                      </button>
                                    )}
                                    <button
                                      className="tbl-btn tbl-btn--danger"
                                      title="Eliminar diagnóstico"
                                      onClick={() => setAnalisisParaEliminar({
                                        loteId: v.lote.id,
                                        vueloId: v.vueloId,
                                        etiqueta: `${v.lote.nombre} · ${fmtFechaVuelo(v.fecha_vuelo)}`,
                                      })}
                                    >
                                      <IconTrash />
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                      <div className="table-footer">
                        <span>Mostrando {pageRows.length} de {vueloRows.length} vuelos</span>
                        <div className="pagination">
                          <button className="page-btn" disabled={page === 1} onClick={() => setPage(p => p - 1)}>‹</button>
                          <span>Página {page} de {totalPages}</span>
                          <button className="page-btn" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>›</button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Vista geoespacial */}
              {mapaExpandido && <div className="mapa-expand-backdrop" onClick={() => setMapaExpandido(false)} />}
              <div className={`card card--mapa${mapaExpandido ? ' card--mapa-expandido' : ''}`}>
                <div className="card-header">
                  <div>
                    <h2 className="card-title">Vista geoespacial</h2>
                    <p className="card-sub">
                      {selectedVuelo
                        ? (selectedVueloRow
                            ? `Análisis — ${selectedVueloRow.lote.nombre} · vuelo del ${fmtFechaVuelo(selectedVueloRow.fecha_vuelo)}`
                            : 'Análisis en curso')
                        : 'Mapa de lotes registrados en la zona norte'}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                    {puedeComparar && (
                      <button
                        className={`card-link${modoComparacion ? ' card-link--active' : ''}`}
                        onClick={() => setModoComparacion(v => !v)}
                        title="Superponer capas de distintas fechas para comparar evolución"
                      >
                        {modoComparacion ? 'Un vuelo' : 'Comparar capas'}
                      </button>
                    )}
                    {selectedVuelo && !modoComparacion && (
                      <button
                        className="card-link"
                        onClick={() => setMapaExpandido((v) => !v)}
                        title={mapaExpandido ? 'Contraer mapa' : 'Expandir mapa'}
                      >
                        {mapaExpandido ? <IconContraer /> : <IconExpandir />}
                        {mapaExpandido ? 'Contraer' : 'Expandir'}
                      </button>
                    )}
                    {selectedVuelo && (
                      <button className="card-link" onClick={() => { setSelectedVuelo(null); setMapaExpandido(false); setModoComparacion(false) }}>
                        Cerrar ×
                      </button>
                    )}
                  </div>
                </div>
                {selectedVuelo && indicesDisponibles.length > 1 && (
                  <div className="indice-switcher">
                    {indicesDisponibles.map((i) => (
                      <button
                        type="button"
                        key={i.indice}
                        className={`indice-switch-btn${selectedVuelo.indice === i.indice ? ' indice-switch-btn--active' : ''}${i.estado === 'error' ? ' indice-switch-btn--error' : ''}`}
                        onClick={() => cambiarIndice(i.indice)}
                        title={i.estado !== 'completado' ? `Estado: ${i.estado}` : ''}
                      >
                        {INDICE_LABEL[i.indice] ?? i.indice}
                      </button>
                    ))}
                  </div>
                )}
                <div className="card-mapa-body">
                  {selectedVuelo && modoComparacion
                    ? (
                      <MapaCapas
                        key={`comparacion-${selectedVuelo.loteId}-${selectedVuelo.indice}`}
                        vuelos={vuelosLoteActivo.map(v => ({
                          vueloId: v.vueloId,
                          loteId: v.lote.id,
                          fecha: v.fecha_vuelo,
                        }))}
                        indice={selectedVuelo.indice}
                        limite={loteRows.find(l => l.id === selectedVuelo.loteId)?.geometry}
                      />
                    )
                    : selectedVuelo
                    ? (
                      <AnalisisMap
                        key={`${selectedVuelo.vueloId}-${selectedVuelo.indice}`}
                        loteId={selectedVuelo.loteId}
                        vueloId={selectedVuelo.vueloId}
                        indice={selectedVuelo.indice}
                        loteAreaHa={selectedVueloRow?.lote?.area_ha ?? null}
                        limite={loteRows.find(l => l.id === selectedVuelo.loteId)?.geometry}
                        onCompletado={loteRows.find(l => l.id === selectedVuelo.loteId)?.geometry ? undefined : cargarDatos}
                      />
                    )
                    : (
                      <div className="mapa-placeholder">
                        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#c2c9b8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                          <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
                          <line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
                        </svg>
                        <p>Seleccioná un vuelo para ver su análisis</p>
                        <p className="empty-hint">Hacé clic en 🔍 en la tabla de arriba</p>
                      </div>
                    )
                  }
                </div>
              </div>
            </div>

            {/* Columna derecha */}
            <div className="dashboard-col-side">
              {/* Actividad reciente */}
              <div className="card">
                <div className="card-header">
                  <h2 className="card-title">Actividad reciente</h2>
                </div>
                <div className="card-body">
                  <div className="actividad-feed">
                    {buildActivityFeed(loteRows, vueloRows, user?.nombre?.split(' ')[0] || 'el usuario').map((item, i) => (
                      <div key={i} className={`actividad-item actividad-item--${item.tipo}`}>
                        <div className="actividad-content">
                          <p className="actividad-texto">{item.texto}</p>
                          <p className="actividad-tiempo">{fmtTiempoRelativo(item.fecha)}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
