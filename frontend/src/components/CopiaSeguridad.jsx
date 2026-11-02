import { useRef, useState } from 'react'
import {
  analizarImportacion,
  cancelarImportacion,
  exportarTodo,
  importarBackup,
} from '../api/backup'
import IconoAdvertencia from './IconoAdvertencia'

const MODOS = [
  {
    valor: 'sumar',
    titulo: 'Sumar a lo que ya tengo',
    detalle: 'Agrega lo que falta y no duplica lo que ya está. Si un lote está en los dos lados, queda el modificado más recientemente.',
  },
  {
    valor: 'reemplazar',
    titulo: 'Reemplazar todo',
    detalle: 'Borra lo que hay en la aplicación y deja exactamente lo del backup. Antes se guarda una copia de lo actual.',
  },
]

function mensajeError(err, fallback) {
  const detail = err.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

function formatearTamano(bytes) {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`
  return `${Math.max(1, Math.round(bytes / 1024 ** 2))} MB`
}

function formatearFecha(iso) {
  return iso ? new Date(iso).toLocaleString('es-AR', { dateStyle: 'medium', timeStyle: 'short' }) : ''
}

function descargar(url) {
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = ''
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
}

function ResumenResultado({ resultado }) {
  const { tablas, archivos } = resultado
  const total = (campo) => Object.values(tablas).reduce((suma, t) => suma + t[campo], 0)
  return (
    <div className="modal-form">
      <p className="success-message">Listo, el backup se importó.</p>
      <ul className="backup-lista">
        <li>{tablas.lotes.insertados} lotes y {tablas.vuelos.insertados} vuelos agregados.</li>
        {resultado.modo === 'sumar' && total('actualizados') > 0 && (
          <li>{total('actualizados')} registros se actualizaron con la versión más reciente del backup.</li>
        )}
        {resultado.modo === 'sumar' && total('omitidos') > 0 && (
          <li>{total('omitidos')} registros ya estaban y no se tocaron.</li>
        )}
        <li>{archivos.copiados} archivos copiados.</li>
        {archivos.faltantes > 0 && <li>{archivos.faltantes} archivos no estaban dentro del backup.</li>}
        {resultado.productos_no_encontrados > 0 && (
          <li>{resultado.productos_no_encontrados} precios cargados se omitieron porque su producto no está en el catálogo.</li>
        )}
        {resultado.copia_previa && <li>Se guardó una copia de lo anterior: {resultado.copia_previa}</li>}
      </ul>
      <div className="modal-actions">
        <button className="btn-primary" onClick={() => window.location.reload()}>Aceptar</button>
      </div>
    </div>
  )
}

export default function CopiaSeguridad() {
  const inputRef = useRef(null)
  const [exportando, setExportando] = useState(false)
  const [analizando, setAnalizando] = useState(false)
  const [importando, setImportando] = useState(false)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const [analisis, setAnalisis] = useState(null)
  const [modo, setModo] = useState('sumar')
  const [confirmarReemplazo, setConfirmarReemplazo] = useState(false)
  const [resultado, setResultado] = useState(null)

  async function handleExportar() {
    setExportando(true)
    setError('')
    setOk('')
    try {
      const datos = await exportarTodo()
      descargar(datos.url_descarga)
      setOk(`Backup creado (${formatearTamano(datos.bytes)}). Se está descargando.`)
    } catch (err) {
      setError(mensajeError(err, 'No se pudo crear el backup.'))
    } finally {
      setExportando(false)
    }
  }

  async function handleElegirArchivo(e) {
    const archivo = e.target.files?.[0]
    e.target.value = ''
    if (!archivo) return
    setAnalizando(true)
    setError('')
    setOk('')
    try {
      setAnalisis(await analizarImportacion(archivo))
      setModo('sumar')
      setConfirmarReemplazo(false)
    } catch (err) {
      setError(mensajeError(err, 'No se pudo leer el archivo.'))
    } finally {
      setAnalizando(false)
    }
  }

  async function cerrar() {
    if (importando) return
    const pendiente = analisis
    setAnalisis(null)
    setResultado(null)
    if (pendiente && !resultado) {
      try { await cancelarImportacion(pendiente.importacion_id) } catch { /* el archivo temporal se limpia solo */ }
    }
  }

  async function handleImportar() {
    if (modo === 'reemplazar' && !confirmarReemplazo) {
      setConfirmarReemplazo(true)
      return
    }
    setImportando(true)
    setError('')
    try {
      setResultado(await importarBackup(analisis.importacion_id, modo))
    } catch (err) {
      setAnalisis(null)
      setError(mensajeError(err, 'No se pudo importar el backup.'))
    } finally {
      setImportando(false)
    }
  }

  const conteos = analisis?.conteos || {}
  const hayDatos = analisis && (analisis.datos_actuales.lotes > 0 || analisis.datos_actuales.vuelos > 0)

  return (
    <div className="card perfil-card">
      <div className="card-header">
        <div>
          <div className="card-title">Copia de seguridad</div>
          <div className="card-sub">Guardá todos tus lotes, vuelos y archivos en un solo archivo, o recuperalos en esta u otra computadora.</div>
        </div>
      </div>
      <div className="card-body perfil-card-body">
        <div className="modal-actions">
          <button type="button" className="btn-primary" onClick={handleExportar} disabled={exportando || analizando}>
            {exportando ? 'Preparando backup...' : 'Exportar todo'}
          </button>
          <button type="button" className="btn-secondary" onClick={() => inputRef.current?.click()} disabled={exportando || analizando}>
            {analizando ? 'Leyendo archivo...' : 'Importar'}
          </button>
          <input ref={inputRef} type="file" accept=".zip" hidden onChange={handleElegirArchivo} />
        </div>
        {(exportando || analizando) && <p className="card-sub">Puede tardar varios minutos si tenés ortomosaicos grandes.</p>}
        {error && <p className="error-message">{error}</p>}
        {ok && <p className="success-message">{ok}</p>}
      </div>

      {analisis && (
        <div className="modal-overlay" onClick={cerrar}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-titulo-con-icono">
                {confirmarReemplazo && <IconoAdvertencia />}
                <h2>{resultado ? 'Importación terminada' : confirmarReemplazo ? '¿Reemplazar todo?' : 'Importar backup'}</h2>
              </div>
              {!resultado && <button className="modal-close" onClick={cerrar} aria-label="Cerrar" disabled={importando}>✕</button>}
            </div>

            {resultado ? <ResumenResultado resultado={resultado} /> : confirmarReemplazo ? (
              <div className="modal-form">
                <p className="confirmar-mensaje">
                  Vas a borrar {analisis.datos_actuales.lotes} lotes y {analisis.datos_actuales.vuelos} vuelos de esta
                  aplicación y dejar solo lo del backup. Antes se guarda una copia de lo actual.
                </p>
                {error && <div className="error-message">{error}</div>}
                <div className="modal-actions">
                  <button className="btn-secondary" onClick={() => setConfirmarReemplazo(false)} disabled={importando}>Volver</button>
                  <button className="btn-danger" onClick={handleImportar} disabled={importando}>
                    {importando ? 'Importando...' : 'Reemplazar todo'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="modal-form">
                <p className="confirmar-mensaje">
                  Backup del {formatearFecha(analisis.creado_en)}: {conteos.lotes || 0} lotes, {conteos.vuelos || 0} vuelos
                  y {analisis.archivos} archivos.
                </p>
                {hayDatos && (
                  <p className="card-sub">
                    Hoy la aplicación tiene {analisis.datos_actuales.lotes} lotes y {analisis.datos_actuales.vuelos} vuelos.
                  </p>
                )}
                {analisis.advertencias.map((a, i) => (
                  <div key={i} className="error-message">{a.mensaje}</div>
                ))}
                <div className="backup-modos">
                  {MODOS.map((m) => (
                    <label key={m.valor} className="backup-modo">
                      <input type="radio" name="modo-importar" checked={modo === m.valor} onChange={() => setModo(m.valor)} />
                      <span><strong>{m.titulo}</strong><br /><span className="card-sub">{m.detalle}</span></span>
                    </label>
                  ))}
                </div>
                {error && <div className="error-message">{error}</div>}
                <div className="modal-actions">
                  <button className="btn-secondary" onClick={cerrar} disabled={importando}>Cancelar</button>
                  <button className="btn-primary" onClick={handleImportar} disabled={importando}>
                    {importando ? 'Importando...' : 'Importar'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
