import { useEffect } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import L from 'leaflet'

const COLORES_CLASE = {
  critica:    '#ef4444',
  deficiente: '#f97316',
  normal:     '#86efac',
  vigorosa:   '#16a34a',
}

const ETIQUETAS_CLASE = {
  critica:    'Crítica',
  deficiente: 'Deficiente',
  normal:     'Normal',
  vigorosa:   'Vigorosa',
}

const COLORES_SEVERIDAD = {
  critica:  '#ef4444',
  moderada: '#f59e0b',
  leve:     '#fbbf24',
  normal:   '#86efac',
  vigorosa: '#3b82f6',
}

const ETIQUETAS_SEVERIDAD = {
  critica:  'Crítica',
  moderada: 'Moderada',
  leve:     'Leve',
  normal:   'Normal',
  vigorosa: 'Vigorosa',
}

function estiloZona(feature) {
  const clase = feature.properties?.clase || 'normal'
  return {
    fillColor: COLORES_CLASE[clase] || '#999',
    fillOpacity: 0.6,
    color: '#fff',
    weight: 1.5,
  }
}

function estiloSeveridad(feature) {
  const severidad = feature.properties?.severidad || 'normal'
  return {
    fillColor: COLORES_SEVERIDAD[severidad] || '#999',
    fillOpacity: 0.6,
    color: '#fff',
    weight: 1.5,
  }
}

function estiloUnidad(feature) {
  const severidad = feature.properties?.severidad || 'normal'
  return {
    fillColor: 'transparent',
    fillOpacity: 0,
    color: COLORES_SEVERIDAD[severidad] || '#666',
    weight: 3,
    dashArray: '8 4',
    opacity: 0.9,
  }
}

function onEachZona(feature, layer) {
  const { clase, ndvi_promedio, area_ha } = feature.properties || {}
  layer.bindPopup(`
    <strong>${ETIQUETAS_CLASE[clase] || clase}</strong><br/>
    NDVI promedio: <strong>${ndvi_promedio?.toFixed(3) ?? '—'}</strong><br/>
    Área: <strong>${area_ha?.toFixed(2) ?? '—'} ha</strong>
  `)
  layer.on({
    mouseover: (e) => e.target.setStyle({ fillOpacity: 0.85, weight: 2.5 }),
    mouseout:  (e) => e.target.setStyle({ fillOpacity: 0.6,  weight: 1.5 }),
  })
}

function onEachZonaSeveridad(feature, layer) {
  const p = feature.properties || {}
  const severidad = ETIQUETAS_SEVERIDAD[p.severidad] || p.severidad || '—'
  layer.bindPopup(`
    <strong>${p.regla_nombre || 'Sin diagnóstico'}</strong><br/>
    Severidad: <strong>${severidad}</strong><br/>
    NDVI: <strong>${p.ndvi_promedio?.toFixed(3) ?? '—'}</strong><br/>
    Área: <strong>${p.area_ha?.toFixed(2) ?? '—'} ha</strong>
  `)
  layer.on({
    mouseover: (e) => e.target.setStyle({ fillOpacity: 0.85, weight: 2.5 }),
    mouseout:  (e) => e.target.setStyle({ fillOpacity: 0.6,  weight: 1.5 }),
  })
}

function onEachUnidad(feature, layer) {
  const p = feature.properties || {}
  layer.bindPopup(`
    <strong>Unidad de manejo #${p.unidad_id}</strong><br/>
    ${p.regla_nombre || ''}<br/>
    ${p.n_zonas} zona${p.n_zonas !== 1 ? 's' : ''} · ${p.area_total_ha} ha
  `)
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

export default function MapaZonas({ geojson, diagnostico }) {
  const modo = diagnostico ? 'severidad' : 'clase'
  const dataMapa = diagnostico || geojson
  const unidades = diagnostico?.unidades_manejo || []

  const featuresKey = `${dataMapa?.features?.length ?? 0}-${modo}`
  const unidadesKey = `u-${unidades.length}`

  const colores = modo === 'severidad' ? COLORES_SEVERIDAD : COLORES_CLASE
  const etiquetas = modo === 'severidad' ? ETIQUETAS_SEVERIDAD : ETIQUETAS_CLASE
  const estilo = modo === 'severidad' ? estiloSeveridad : estiloZona
  const onEach = modo === 'severidad' ? onEachZonaSeveridad : onEachZona

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
        {dataMapa && (
          <>
            <GeoJSON key={featuresKey} data={dataMapa} style={estilo} onEachFeature={onEach} />
            {unidades.length > 0 && (
              <GeoJSON
                key={unidadesKey}
                data={{ type: 'FeatureCollection', features: unidades }}
                style={estiloUnidad}
                onEachFeature={onEachUnidad}
              />
            )}
            <FitBounds geojson={dataMapa} />
          </>
        )}
      </MapContainer>

      <div className="mapa-leyenda">
        {Object.entries(etiquetas).map(([key, label]) => (
          <div key={key} className="leyenda-item">
            <span className="leyenda-color" style={{ background: colores[key] }} />
            <span>{label}</span>
          </div>
        ))}
        {unidades.length > 0 && (
          <div className="leyenda-item">
            <span
              className="leyenda-color"
              style={{ background: 'transparent', border: '2px dashed #666' }}
            />
            <span>Unidad de manejo</span>
          </div>
        )}
      </div>
    </div>
  )
}
