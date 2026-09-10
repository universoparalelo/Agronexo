import { useState, useCallback, useEffect } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import client from '../api/client'
import MapaDibujoLote from './MapaDibujoLote'
import { AREA_MIN_HA, AREA_MAX_HA, tieneAutointerseccion } from '../utils/geometria'

const CULTIVOS = [
  { value: 'soja', label: 'Soja' },
  { value: 'maiz', label: 'Maíz' },
  { value: 'algodon', label: 'Algodón' },
  { value: 'sorgo', label: 'Sorgo' },
]

const TIPOS_SUELO = [
  { value: '', label: 'Seleccionar...' },
  { value: 'arcilloso', label: 'Arcilloso' },
  { value: 'franco', label: 'Franco' },
  { value: 'franco_arcilloso', label: 'Franco arcilloso' },
  { value: 'franco_arenoso', label: 'Franco arenoso' },
  { value: 'arenoso', label: 'Arenoso' },
  { value: 'vertisol', label: 'Vertisol' },
  { value: 'otro', label: 'Otro' },
]

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

function extraerPoligono(geojson) {
  if (geojson.type === 'Polygon') return geojson
  if (geojson.type === 'Feature' && geojson.geometry?.type === 'Polygon')
    return geojson.geometry
  if (geojson.type === 'FeatureCollection') {
    const feat = geojson.features?.find((f) => f.geometry?.type === 'Polygon')
    if (feat) return feat.geometry
  }
  return null
}

export default function ModalNuevoLote({ onSuccess, onClose }) {
  const [form, setForm] = useState({
    nombre: '', cultivo: 'soja', estadio_fenologico: '',
    variedad: '', tipo_suelo: '', fecha_siembra: '',
  })
  const [modoLimite, setModoLimite] = useState('dibujar')
  const [poligono, setPoligono] = useState(null)
  const [areaM2, setAreaM2] = useState(null)
  const [autointerseccion, setAutointerseccion] = useState(false)
  const [bounds, setBounds] = useState(null)
  const [archivoNombre, setArchivoNombre] = useState('')
  const [dragActivo, setDragActivo] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const areaHa = areaM2 != null ? areaM2 / 10000 : null
  const areaFueraDeRango = areaHa != null && (areaHa < AREA_MIN_HA || areaHa > AREA_MAX_HA)

  function cambiarModo(modo) {
    setModoLimite(modo)
    setPoligono(null)
    setAreaM2(null)
    setAutointerseccion(false)
    setBounds(null)
    setArchivoNombre('')
    setError('')
  }

  function onDibujoChange(geojson, areaCalculadaM2, autointerseccionDetectada) {
    setPoligono(geojson)
    setAreaM2(areaCalculadaM2)
    setAutointerseccion(!!autointerseccionDetectada)
    setError('')
  }

  function handleField(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  function procesarArchivo(file) {
    setError('')
    setPoligono(null)
    setAutointerseccion(false)
    setBounds(null)
    setArchivoNombre(file.name)

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const json = JSON.parse(e.target.result)
        const poly = extraerPoligono(json)
        if (!poly) {
          setError('El archivo no contiene un Polygon GeoJSON válido.')
          return
        }
        setPoligono(poly)
        setAutointerseccion(tieneAutointerseccion(poly.coordinates[0]))
        setBounds(boundsDesdePoligono(poly.coordinates))
      } catch {
        setError('El archivo no es un JSON válido.')
      }
    }
    reader.readAsText(file)
  }

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragActivo(false)
    const file = e.dataTransfer.files[0]
    if (file) procesarArchivo(file)
  }, [])

  function onFileChange(e) {
    const file = e.target.files[0]
    if (file) procesarArchivo(file)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.nombre.trim()) { setError('El nombre del lote es requerido.'); return }
    if (autointerseccion) {
      setError('El polígono tiene lados que se cruzan entre sí — corregilo antes de continuar.')
      return
    }
    if (areaFueraDeRango) {
      setError(`El área del polígono (${areaHa.toFixed(2)} ha) está fuera del rango esperado (${AREA_MIN_HA}-${AREA_MAX_HA} ha).`)
      return
    }

    setLoading(true)
    setError('')
    try {
      const { data } = await client.post('/lotes', {
        nombre: form.nombre.trim(),
        cultivo: form.cultivo,
        estadio_fenologico: form.estadio_fenologico.trim() || null,
        variedad: form.variedad.trim() || null,
        tipo_suelo: form.tipo_suelo || null,
        fecha_siembra: form.fecha_siembra ? new Date(form.fecha_siembra).toISOString() : null,
        geometry: poligono,
      })
      onSuccess(data.id)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : detail || 'Error al crear el lote.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--limites" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Nuevo lote</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
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
              <label htmlFor="estadio">Estadio fenológico <span className="label-opcional">(opcional)</span></label>
              <input
                id="estadio"
                name="estadio_fenologico"
                type="text"
                placeholder="Ej: R3"
                maxLength={30}
                value={form.estadio_fenologico}
                onChange={handleField}
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="variedad">Variedad <span className="label-opcional">(opcional)</span></label>
              <input
                id="variedad"
                name="variedad"
                type="text"
                placeholder="Ej: DM 46i17"
                maxLength={100}
                value={form.variedad}
                onChange={handleField}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="tipo_suelo">Tipo de suelo <span className="label-opcional">(opcional)</span></label>
              <select id="tipo_suelo" name="tipo_suelo" value={form.tipo_suelo} onChange={handleField} disabled={loading}>
                {TIPOS_SUELO.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="fecha_siembra">Fecha de siembra <span className="label-opcional">(opcional)</span></label>
            <input
              id="fecha_siembra"
              name="fecha_siembra"
              type="date"
              value={form.fecha_siembra}
              onChange={handleField}
              disabled={loading}
            />
          </div>

          <p className="limites-hint">
            Límite del lote <span className="label-opcional">(opcional)</span> — dibujalo sobre el mapa satelital o subí un archivo <strong>.geojson</strong> si ya lo tenés. Podés cargarlo más adelante desde "Límites".
          </p>

          <div className="modo-limite-toggle">
            <button
              type="button"
              className={`modo-limite-btn${modoLimite === 'dibujar' ? ' modo-limite-btn--activo' : ''}`}
              onClick={() => cambiarModo('dibujar')}
              disabled={loading}
            >
              🗺️ Dibujar en mapa
            </button>
            <button
              type="button"
              className={`modo-limite-btn${modoLimite === 'subir' ? ' modo-limite-btn--activo' : ''}`}
              onClick={() => cambiarModo('subir')}
              disabled={loading}
            >
              📄 Subir GeoJSON
            </button>
          </div>

          {modoLimite === 'dibujar' ? (
            <>
              <div className="limites-preview-map">
                <MapaDibujoLote onChange={onDibujoChange} height={300} />
              </div>
              {areaHa != null && (
                <p className={`area-badge${areaFueraDeRango ? ' area-badge--alerta' : ''}`}>
                  Área del polígono: {areaHa.toFixed(2)} ha
                  {areaFueraDeRango && ' — fuera del rango esperado para un lote agrícola'}
                </p>
              )}
              {autointerseccion && (
                <p className="area-badge area-badge--alerta">
                  ⚠️ El polígono tiene lados que se cruzan entre sí — corregilo antes de confirmar.
                </p>
              )}
            </>
          ) : (
            <>
              <div
                className={`dropzone${dragActivo ? ' dropzone--activo' : ''}${poligono ? ' dropzone--ok' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragActivo(true) }}
                onDragLeave={() => setDragActivo(false)}
                onDrop={onDrop}
                onClick={() => document.getElementById('input-geojson-nuevo-lote').click()}
              >
                <input
                  id="input-geojson-nuevo-lote"
                  type="file"
                  accept=".geojson,.json"
                  style={{ display: 'none' }}
                  onChange={onFileChange}
                />
                {poligono ? (
                  <span className="dropzone-archivo">✓ {archivoNombre}</span>
                ) : (
                  <>
                    <span className="dropzone-icono">📍</span>
                    <span className="dropzone-hint">Arrastrá o hacé clic para seleccionar</span>
                    <span className="dropzone-ext">.geojson / .json</span>
                  </>
                )}
              </div>

              {poligono && bounds && (
                <div className="limites-preview-map">
                  <MapContainer
                    bounds={bounds}
                    style={{ height: '220px', width: '100%', borderRadius: '8px' }}
                    zoomControl={true}
                    scrollWheelZoom={false}
                  >
                    <TileLayer
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                      attribution="© OpenStreetMap contributors"
                    />
                    <GeoJSON
                      data={poligono}
                      style={{ color: '#2ecc71', weight: 2, fillOpacity: 0.15 }}
                    />
                    <FitBounds bounds={bounds} />
                  </MapContainer>
                </div>
              )}
              {autointerseccion && (
                <p className="area-badge area-badge--alerta">
                  ⚠️ El polígono tiene lados que se cruzan entre sí — corregilo antes de confirmar.
                </p>
              )}
            </>
          )}

          {error && <div className="error-message">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Creando...' : 'Crear lote'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
