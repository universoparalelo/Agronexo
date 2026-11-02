import { TileLayer } from 'react-leaflet'
import { useConexion } from '../hooks/useConexion'

// Un píxel transparente: sin esto, un mosaico que no llega muestra el ícono de imagen rota.
const MOSAICO_VACIO = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'

// Mapa de fondo de internet (OpenStreetMap, Esri...). Sin conexión no se pide nada:
// queda el color liso del mapa (`.leaflet-container`) con los polígonos encima.
export default function CapaBase(props) {
  const hayConexion = useConexion()
  if (!hayConexion) return null
  return <TileLayer errorTileUrl={MOSAICO_VACIO} {...props} />
}
