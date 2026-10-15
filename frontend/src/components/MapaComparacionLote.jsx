import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import L from 'leaflet'
import MapaZonas from './MapaZonas'

const COLORES_CLASE = {
  critica:    '#ef4444',
  deficiente: '#f97316',
  normal:     '#86efac',
  vigorosa:   '#16a34a',
}

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function estiloZona(feature) {
  const clase = feature.properties?.clase || 'normal'
  return { fillColor: COLORES_CLASE[clase] || '#999', color: '#fff', weight: 1 }
}

function AutoResize() {
  const map = useMap()
  useEffect(() => {
    const contenedor = map.getContainer()
    const observer = new ResizeObserver(() => map.invalidateSize())
    observer.observe(contenedor)
    return () => observer.disconnect()
  }, [map])
  return null
}

function FitBoundsUnion({ featuresA, featuresB }) {
  const map = useMap()
  useEffect(() => {
    const todas = [...featuresA, ...featuresB]
    if (!todas.length) return
    try {
      const bounds = L.geoJSON({ type: 'FeatureCollection', features: todas }).getBounds()
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20] })
    } catch { /* ignora: el mapa se queda en su vista inicial */ }
  }, [featuresA, featuresB, map])
  return null
}

// Pestaña "Cortina": un único mapa Leaflet con las zonas del vuelo base
// siempre visibles y las del vuelo actual superpuestas — un slider controla
// la opacidad de la capa "actual" en vivo (setStyle imperativo sobre la capa
// ya montada, no remount, para no perder el pan/zoom mientras se arrastra).
function MapaCortina({ featuresBase, featuresActual, fechaBase, fechaActual }) {
  const [opacidad, setOpacidad] = useState(0.5)
  const capaActualRef = useRef(null)

  useEffect(() => {
    capaActualRef.current?.setStyle((feature) => ({ ...estiloZona(feature), fillOpacity: opacidad }))
  }, [opacidad])

  const geojsonBase = { type: 'FeatureCollection', features: featuresBase }
  const geojsonActual = { type: 'FeatureCollection', features: featuresActual }

  return (
    <div className="mapa-comparacion-cortina">
      <div className="mapa-comparacion-mapa-wrap">
        <MapContainer center={[-27.47, -60.67]} zoom={13} className="mapa-comparacion-mapa" scrollWheelZoom>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap' />
          <AutoResize />
          <FitBoundsUnion featuresA={featuresBase} featuresB={featuresActual} />
          <GeoJSON key="base" data={geojsonBase} style={(f) => ({ ...estiloZona(f), fillOpacity: 0.75 })} />
          <GeoJSON key="actual" ref={capaActualRef} data={geojsonActual} style={(f) => ({ ...estiloZona(f), fillOpacity: opacidad })} />
        </MapContainer>
      </div>

      <div className="mapa-comparacion-slider-fila">
        <span className="mapa-comparacion-slider-label">Base · {fechaCorta(fechaBase)}</span>
        <input
          type="range" min="0" max="100" value={Math.round(opacidad * 100)}
          onChange={(e) => setOpacidad(Number(e.target.value) / 100)}
          className="mapa-comparacion-slider"
          aria-label="Opacidad del vuelo actual superpuesto sobre el base"
        />
        <span className="mapa-comparacion-slider-label">Actual · {fechaCorta(fechaActual)}</span>
      </div>
    </div>
  )
}

function MapaLadoLado({ featuresBase, featuresActual, fechaBase, fechaActual }) {
  return (
    <div className="mapa-comparacion-lado-lado">
      <div className="mapa-comparacion-mini mapa-comparacion-mini--actual">
        <span className="mapa-comparacion-pill mapa-comparacion-pill--actual">Actual · {fechaCorta(fechaActual)}</span>
        <MapaZonas geojson={{ type: 'FeatureCollection', features: featuresActual }} interactivo={false} />
      </div>
      <div className="mapa-comparacion-mini mapa-comparacion-mini--base">
        <span className="mapa-comparacion-pill">Base · {fechaCorta(fechaBase)}</span>
        <MapaZonas geojson={{ type: 'FeatureCollection', features: featuresBase }} interactivo={false} />
      </div>
    </div>
  )
}

// Dos formas de ver las zonas de los dos vuelos comparados — ambas sobre
// datos reales (GeoJSON de cada vuelo), nunca una ilustración estática.
// El tab activo ("lado-a-lado" | "cortina") lo controla el padre
// (ResultadosVuelo.jsx), que también decide cuándo mostrar la "vista
// completa" (los dos paneles enteros) en lugar de este componente — un solo
// selector para las 3 formas de ver el mapa, no secciones duplicadas.
// "Mapa de cambio" (raster real vuelo B − vuelo A) queda fuera de alcance
// acá, ver "Problemas abiertos" de HU-R4-09.
export default function MapaComparacionLote({ vueloA, vueloB, featuresA, featuresB, tab }) {
  const esBPosterior = new Date(vueloB.fecha_vuelo) >= new Date(vueloA.fecha_vuelo)
  const [vueloBase, vueloActual] = esBPosterior ? [vueloA, vueloB] : [vueloB, vueloA]
  const [featuresBase, featuresActual] = esBPosterior ? [featuresA, featuresB] : [featuresB, featuresA]

  if (!featuresBase.length && !featuresActual.length) return null

  return (
    <div className="mapa-comparacion-lote">
      {tab === 'lado-a-lado' ? (
        <MapaLadoLado
          featuresBase={featuresBase} featuresActual={featuresActual}
          fechaBase={vueloBase.fecha_vuelo} fechaActual={vueloActual.fecha_vuelo}
        />
      ) : (
        <MapaCortina
          featuresBase={featuresBase} featuresActual={featuresActual}
          fechaBase={vueloBase.fecha_vuelo} fechaActual={vueloActual.fecha_vuelo}
        />
      )}
    </div>
  )
}
