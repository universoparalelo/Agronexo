import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'

function boundsDesdePoligono(coords) {
  const ring = coords[0]
  const lngs = ring.map((c) => c[0])
  const lats = ring.map((c) => c[1])
  return [
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)],
  ]
}

const ESTILO_POLIGONO = { color: '#2d7a3d', weight: 2, fillColor: '#2d7a3d', fillOpacity: 0.18 }

export default function MiniMapaLote({ geometry }) {
  if (!geometry) {
    return (
      <div className="mini-mapa-sin-limites">
        <span>Sin límites definidos</span>
      </div>
    )
  }

  let bounds
  try {
    bounds = boundsDesdePoligono(geometry.coordinates)
  } catch {
    return null
  }

  return (
    <div className="mini-mapa-lote">
      <MapContainer
        bounds={bounds}
        boundsOptions={{ padding: [8, 8] }}
        zoomControl={false}
        scrollWheelZoom={false}
        dragging={false}
        touchZoom={false}
        doubleClickZoom={false}
        keyboard={false}
        attributionControl={false}
        style={{ height: '110px', width: '100%' }}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <GeoJSON data={geometry} style={ESTILO_POLIGONO} />
      </MapContainer>
    </div>
  )
}
