import { useEffect } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import L from 'leaflet'

const COLORES = {
  critica:    '#ef4444',
  deficiente: '#f97316',
  normal:     '#86efac',
  vigorosa:   '#16a34a',
}

const ETIQUETAS = {
  critica:    'Crítica',
  deficiente: 'Deficiente',
  normal:     'Normal',
  vigorosa:   'Vigorosa',
}

function estiloZona(feature) {
  const clase = feature.properties?.clase || 'normal'
  return {
    fillColor: COLORES[clase] || '#999',
    fillOpacity: 0.6,
    color: '#fff',
    weight: 1.5,
  }
}

function onEachFeature(feature, layer) {
  const { clase, ndvi_promedio, area_ha } = feature.properties || {}
  layer.bindPopup(`
    <strong>${ETIQUETAS[clase] || clase}</strong><br/>
    NDVI promedio: <strong>${ndvi_promedio?.toFixed(3) ?? '—'}</strong><br/>
    Área: <strong>${area_ha?.toFixed(2) ?? '—'} ha</strong>
  `)
  layer.on({
    mouseover: (e) => e.target.setStyle({ fillOpacity: 0.85, weight: 2.5 }),
    mouseout:  (e) => e.target.setStyle({ fillOpacity: 0.6,  weight: 1.5 }),
  })
}

function FitBounds({ geojson }) {
  const map = useMap()
  useEffect(() => {
    if (!geojson) return
    try {
      const layer = L.geoJSON(geojson)
      const bounds = layer.getBounds()
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [24, 24] })
    } catch (_) {}
  }, [geojson, map])
  return null
}

export default function MapaZonas({ geojson }) {
  const featuresKey = geojson?.features?.length ?? 0

  return (
    <div className="mapa-zonas-wrapper">
      <MapContainer
        center={[-27.47, -60.67]}
        zoom={13}
        className="mapa-zonas"
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        {geojson && (
          <>
            <GeoJSON key={featuresKey} data={geojson} style={estiloZona} onEachFeature={onEachFeature} />
            <FitBounds geojson={geojson} />
          </>
        )}
      </MapContainer>

      <div className="mapa-leyenda">
        {Object.entries(ETIQUETAS).map(([clase, label]) => (
          <div key={clase} className="leyenda-item">
            <span className="leyenda-color" style={{ background: COLORES[clase] }} />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
