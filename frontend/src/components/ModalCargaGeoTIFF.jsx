import { useRef, useState } from 'react'
import client from '../api/client'

const CULTIVOS = [
  { value: 'soja', label: 'Soja' },
  { value: 'maiz', label: 'Maíz' },
  { value: 'algodon', label: 'Algodón' },
  { value: 'sorgo', label: 'Sorgo' },
]

const SENSORES = [
  { value: 'sentinel2', label: 'Sentinel-2' },
  { value: 'dji_mavic3', label: 'DJI Mavic 3 Multispectral' },
]

export default function ModalCargaGeoTIFF({ onSuccess, onClose }) {
  const [form, setForm] = useState({
    nombre: '',
    cultivo: 'soja',
    sensor: 'sentinel2',
    estadio_fenologico: '',
  })
  const [archivo, setArchivo] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef()

  function handleField(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
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

  async function handleSubmit(e) {
    e.preventDefault()
    if (!archivo) { setError('Seleccioná un archivo GeoTIFF.'); return }
    if (!form.nombre.trim()) { setError('El nombre del lote es requerido.'); return }

    const fd = new FormData()
    fd.append('archivo', archivo)
    fd.append('nombre', form.nombre.trim())
    fd.append('cultivo', form.cultivo)
    fd.append('sensor', form.sensor)
    if (form.estadio_fenologico.trim()) {
      fd.append('estadio_fenologico', form.estadio_fenologico.trim())
    }

    setLoading(true)
    setError('')
    try {
      const { data } = await client.post('/lotes/desde-geotiff', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      onSuccess(data.lote_id)
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Error al subir el archivo. Verificá que sea un GeoTIFF válido.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Cargar GeoTIFF</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">×</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label htmlFor="nombre">Nombre del lote</label>
            <input
              id="nombre"
              name="nombre"
              type="text"
              placeholder="Ej: Lote Norte — Parcela 3"
              value={form.nombre}
              onChange={handleField}
              disabled={loading}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="cultivo">Cultivo</label>
              <select id="cultivo" name="cultivo" value={form.cultivo} onChange={handleField} disabled={loading}>
                {CULTIVOS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="sensor">Sensor</label>
              <select id="sensor" name="sensor" value={form.sensor} onChange={handleField} disabled={loading}>
                {SENSORES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="estadio">Estadio fenológico <span className="label-opcional">(opcional)</span></label>
            <input
              id="estadio"
              name="estadio_fenologico"
              type="text"
              placeholder="Ej: R3"
              maxLength={10}
              value={form.estadio_fenologico}
              onChange={handleField}
              disabled={loading}
            />
          </div>

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
                <p className="dropzone-icono">📁</p>
                <p className="dropzone-hint">Arrastrá el archivo acá o hacé clic para seleccionarlo</p>
                <p className="dropzone-ext">.tif / .tiff</p>
              </>
            )}
          </div>

          {error && <p className="error-message">{error}</p>}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={loading || !archivo}>
              {loading ? 'Subiendo...' : 'Iniciar análisis'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
