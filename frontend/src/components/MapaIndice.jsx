import { useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'

// El contenedor del mapa cambia de tamaño (botón "Expandir"/"Contraer") sin que
// MapContainer se desmonte — Leaflet cachea el tamaño inicial y no lo actualiza
// solo, así que los tiles quedan mal recortados hasta forzar invalidateSize().
function InvalidarAlRedimensionar() {
  const map = useMap()
  useEffect(() => {
    const contenedor = map.getContainer()
    const ro = new ResizeObserver(() => map.invalidateSize())
    ro.observe(contenedor)
    return () => ro.disconnect()
  }, [map])
  return null
}

const COLORES_CLASE = {
  critica:    '#c0392b',
  deficiente: '#e67e22',
  normal:     '#f1c40f',
  vigorosa:   '#27ae60',
}

const ETIQUETAS_CLASE = {
  critica:    'Crítica (NDVI < 0.2)',
  deficiente: 'Deficiente (0.2–0.4)',
  normal:     'Normal (0.4–0.7)',
  vigorosa:   'Vigorosa (> 0.7)',
}

function styleFeature(feature) {
  const clase = feature?.properties?.clase
  return {
    fillColor: COLORES_CLASE[clase] ?? '#aaa',
    fillOpacity: 0.65,
    color: '#fff',
    weight: 1.2,
  }
}

function onEachFeature(feature, layer) {
  const p = feature?.properties
  if (!p) return
  const ndvi = p.ndvi_promedio != null ? p.ndvi_promedio.toFixed(3) : '–'
  const area = p.area_ha != null
    ? p.area_ha.toLocaleString('es-AR', { maximumFractionDigits: 1 })
    : '–'
  layer.bindTooltip(
    `<strong style="text-transform:capitalize">${p.clase ?? 'zona'}</strong>` +
    `<br/>NDVI prom.: ${ndvi}` +
    `<br/>Área: ${area} ha`,
    { sticky: true, className: 'mapa-tooltip' }
  )
}

export default function MapaIndice({ geojson }) {
  const bounds = useMemo(() => {
    if (!geojson?.features?.length) return null
    const allCoords = geojson.features.flatMap((f) => {
      const type = f.geometry?.type
      const raw = f.geometry?.coordinates
      if (!raw) return []
      if (type === 'Polygon') return raw.flat(1)
      if (type === 'MultiPolygon') return raw.flat(2)
      return []
    })
    if (!allCoords.length) return null
    const lngs = allCoords.map((c) => c[0])
    const lats = allCoords.map((c) => c[1])
    return [
      [Math.min(...lats), Math.min(...lngs)],
      [Math.max(...lats), Math.max(...lngs)],
    ]
  }, [geojson])

  if (!geojson) return null

  return (
    <div className="mapa-indice-wrap">
      <MapContainer
        bounds={bounds ?? [[-34, -64], [-22, -53]]}
        boundsOptions={{ padding: [20, 20] }}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        <GeoJSON
          key={geojson.features?.length}
          data={geojson}
          style={styleFeature}
          onEachFeature={onEachFeature}
        />
        <InvalidarAlRedimensionar />
      </MapContainer>

      <div className="mapa-leyenda">
        {Object.entries(COLORES_CLASE).map(([clase, color]) => (
          <div key={clase} className="leyenda-item">
            <span className="leyenda-color" style={{ background: color }} />
            <span className="leyenda-label">{ETIQUETAS_CLASE[clase]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
