import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import provincias from '../data/nea-provincias.json'

// Chaco, Formosa, Corrientes y Misiones — foco geográfico del proyecto. Los
// polígonos son un extracto simplificado de OpenStreetMap (ver atribución).
const BOUNDS_NEA = [[-30.6, -63.2], [-21.6, -53.4]]

const ESTILO_PROVINCIA = { color: '#ffffff', weight: 2, fillColor: '#7bc043', fillOpacity: 0.2 }

function etiquetar(feature, layer) {
  layer.bindTooltip(feature.properties.nombre, {
    permanent: true,
    direction: 'center',
    className: 'etiqueta-provincia',
  })
}

// Mapa de referencia para cuando todavía no hay una ubicación que mostrar.
export default function MapaNEA({ aviso }) {
  return (
    <div className="mapa-nea">
      <MapContainer bounds={BOUNDS_NEA} style={{ height: '100%', width: '100%' }} scrollWheelZoom={false}>
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution="Tiles &copy; Esri | Límites provinciales &copy; colaboradores de OpenStreetMap"
        />
        <GeoJSON data={provincias} style={ESTILO_PROVINCIA} onEachFeature={etiquetar} interactive={false} />
      </MapContainer>
      {aviso && <div className="mapa-nea-aviso">{aviso}</div>}
    </div>
  )
}
