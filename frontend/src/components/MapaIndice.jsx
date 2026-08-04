import { Component, useEffect, useMemo } from 'react'
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

// Límite de seguridad: más de 1 500 polígonos causa lentitud extrema o crash en
// navegadores de gama baja. Mostramos advertencia en lugar de intentar renderizar.
const MAX_FEATURES_RENDER = 1500

// Error boundary de clase — única forma de capturar errores de render en React.
class MapaBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }
  static getDerivedStateFromError(err) {
    return { error: err?.message ?? 'Error desconocido' }
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: '1.5rem', color: '#b91c1c', fontSize: '0.85rem' }}>
          <strong>No se pudo renderizar el mapa.</strong>
          <br />
          {this.state.error}
        </div>
      )
    }
    return this.props.children
  }
}

export default function MapaIndice({ geojson }) {
  const nFeatures = geojson?.features?.length ?? 0

  const bounds = useMemo(() => {
    if (!nFeatures) return null
    // Iterar con loop en lugar de spread+Math.min/max — el spread falla con stack
    // overflow cuando hay miles de polígonos con decenas de coordenadas cada uno.
    let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity
    for (const f of geojson.features) {
      const type = f.geometry?.type
      const raw = f.geometry?.coordinates
      if (!raw) continue
      const rings = type === 'Polygon' ? raw : type === 'MultiPolygon' ? raw.flat(1) : []
      for (const ring of rings) {
        for (const [lng, lat] of ring) {
          if (lat < minLat) minLat = lat
          if (lat > maxLat) maxLat = lat
          if (lng < minLng) minLng = lng
          if (lng > maxLng) maxLng = lng
        }
      }
    }
    if (minLat === Infinity) return null
    return [[minLat, minLng], [maxLat, maxLng]]
  }, [geojson, nFeatures])

  if (!geojson) return null

  if (nFeatures > MAX_FEATURES_RENDER) {
    return (
      <div style={{ padding: '1.5rem', fontSize: '0.85rem', color: '#6b7280' }}>
        <strong style={{ color: '#b45309' }}>Resultado demasiado grande para visualizar</strong>
        <br />
        El análisis generó <strong>{nFeatures}</strong> polígonos. El mapa solo puede mostrar
        hasta {MAX_FEATURES_RENDER.toLocaleString()}.
        <br /><br />
        Intentá aumentar el umbral de área mínima al cargar el próximo vuelo, o usá la exportación
        Shapefile para visualizar en QGIS.
      </div>
    )
  }

  return (
    <MapaBoundary>
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
            key={nFeatures}
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
    </MapaBoundary>
  )
}
