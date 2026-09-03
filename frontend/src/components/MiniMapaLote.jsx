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

export default function MiniMapaLote({ geometry, expandido = false }) {
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
    <div className={expandido ? 'mini-mapa-lote mini-mapa-lote--expandido' : 'mini-mapa-lote'}>
      <MapContainer
        bounds={bounds}
        boundsOptions={{ padding: [20, 20] }}
        zoomControl={expandido}
        scrollWheelZoom={expandido}
        dragging={expandido}
        touchZoom={expandido}
        doubleClickZoom={expandido}
        keyboard={expandido}
        attributionControl={expandido}
        style={{ height: expandido ? '100%' : '110px', width: '100%' }}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <GeoJSON data={geometry} style={ESTILO_POLIGONO} />
      </MapContainer>
    </div>
  )
}
