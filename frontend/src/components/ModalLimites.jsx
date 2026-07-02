import { useState, useCallback, useEffect } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import client from '../api/client'

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

export default function ModalLimites({ lote, onSuccess, onClose }) {
  const [poligono, setPoligono] = useState(null)
  const [bounds, setBounds] = useState(null)
  const [archivoNombre, setArchivoNombre] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [dragActivo, setDragActivo] = useState(false)

  function procesarArchivo(file) {
    setError('')
    setPoligono(null)
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

  async function handleGuardar() {
    if (!poligono) return
    setLoading(true)
    setError('')
    try {
      await client.put(`/lotes/${lote.id}`, { geometry: poligono })
      onSuccess()
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : detail || 'Error al guardar el límite.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--limites" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Límites del lote — {lote.nombre}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <div className="modal-form">
          <p className="limites-hint">
            Subí un archivo <strong>.geojson</strong> con el polígono del límite del lote.
          </p>

          <div
            className={`dropzone${dragActivo ? ' dropzone--activo' : ''}${poligono ? ' dropzone--ok' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragActivo(true) }}
            onDragLeave={() => setDragActivo(false)}
            onDrop={onDrop}
            onClick={() => document.getElementById('input-geojson').click()}
          >
            <input
              id="input-geojson"
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
                style={{ height: '260px', width: '100%', borderRadius: '8px' }}
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

          {error && <div className="error-message">{error}</div>}

          <div className="modal-actions">
            <button className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button
              className="btn-primary"
              onClick={handleGuardar}
              disabled={!poligono || loading}
            >
              {loading ? 'Guardando...' : 'Guardar límites'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
