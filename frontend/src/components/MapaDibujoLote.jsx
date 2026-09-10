import { useEffect, useRef, useCallback, useState } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import '@geoman-io/leaflet-geoman-free'
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css'
import { areaGeodesicaM2, tieneAutointerseccion } from '../utils/geometria'

// Resistencia, Chaco — centro por defecto del mapa (foco geográfico NEA)
const CENTRO_NEA = [-27.45, -59.05]

function ControlesDibujo({ onChange, initialGeoJSON }) {
  const map = useMap()
  const capaRef = useRef(null)

  const emitir = useCallback(
    (layer) => {
      if (!layer) {
        onChange(null, null, false)
        return
      }
      const geojson = layer.toGeoJSON().geometry
      const areaM2 = areaGeodesicaM2(layer.getLatLngs()[0])
      const autointerseccion = tieneAutointerseccion(geojson.coordinates[0])
      onChange(geojson, areaM2, autointerseccion)
    },
    [onChange]
  )

  const reemplazarCapa = useCallback(
    (layer) => {
      if (capaRef.current && capaRef.current !== layer) {
        map.removeLayer(capaRef.current)
      }
      capaRef.current = layer
    },
    [map]
  )

  useEffect(() => {
    map.pm.addControls({
      position: 'topright',
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawCircle: false,
      drawText: false,
      drawRectangle: true,
      drawPolygon: true,
      editMode: true,
      dragMode: true,
      cutPolygon: false,
      removalMode: true,
      rotateMode: false,
    })

    function vincularEventosCapa(layer) {
      layer.on('pm:edit', () => emitir(layer))
      layer.on('pm:dragend', () => emitir(layer))
    }

    function onCreate(e) {
      // Un solo polígono activo por lote: la figura nueva reemplaza a la anterior.
      reemplazarCapa(e.layer)
      vincularEventosCapa(e.layer)
      emitir(e.layer)
    }

    function onRemove(e) {
      if (capaRef.current === e.layer) {
        capaRef.current = null
        emitir(null)
      }
    }

    map.on('pm:create', onCreate)
    map.on('pm:remove', onRemove)

    if (initialGeoJSON) {
      const layer = L.geoJSON(initialGeoJSON).getLayers()[0]
      layer.addTo(map)
      layer.pm.enable()
      reemplazarCapa(layer)
      vincularEventosCapa(layer)
      map.fitBounds(layer.getBounds(), { padding: [20, 20] })
      emitir(layer)
    }

    return () => {
      map.off('pm:create', onCreate)
      map.off('pm:remove', onRemove)
      map.pm.removeControls()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map])

  return null
}

export default function MapaDibujoLote({
  onChange,
  initialGeoJSON = null,
  center = CENTRO_NEA,
  zoom = 14,
  height = 320,
}) {
  const [mostrarReferencia, setMostrarReferencia] = useState(true)

  return (
    <div className="mapa-dibujo-wrapper">
      <button
        type="button"
        className="mapa-toggle-referencia"
        onClick={() => setMostrarReferencia((v) => !v)}
      >
        {mostrarReferencia ? '🏷️ Ocultar límites y nombres' : '🏷️ Mostrar límites y nombres'}
      </button>
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height, width: '100%', borderRadius: '8px' }}
        scrollWheelZoom
      >
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics"
          maxZoom={19}
        />
        {mostrarReferencia && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
            maxZoom={19}
            // Capa de referencia (límites político-administrativos + toponimia) sobre el
            // satelital de Esri — comparte proveedor, no agrega texto de atribución nuevo.
          />
        )}
        <ControlesDibujo onChange={onChange} initialGeoJSON={initialGeoJSON} />
      </MapContainer>
    </div>
  )
}
