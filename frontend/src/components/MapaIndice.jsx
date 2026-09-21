import { Component, useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import { ETIQUETA_CLASE, etiquetaClase } from '../utils/clasesIndice'
import PatronSinDatos, { ESTILO_SIN_DATOS, TEXTO_SIN_DATOS } from './PatronSinDatos'

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
  normal:     '#8fd16f',
  vigorosa:   '#1e8449',
}

// Umbrales "fijo" por índice — deben coincidir con
// workers/gis/clasificacion.py::_UMBRALES_POR_INDICE. Cada índice tiene su
// propio rango agronómico típico (NDRE ronda 0.1-0.4 para el mismo canopeo
// donde NDVI ronda 0.4-0.8), por eso no se reutilizan los umbrales de NDVI
// para los demás.
const UMBRALES_FIJOS = {
  ndvi:  [0.20, 0.40, 0.70],
  gndvi: [0.25, 0.45, 0.60],
  ndre:  [0.10, 0.20, 0.35],
  savi:  [0.15, 0.30, 0.50],
  exg:   [0.05, 0.15, 0.30],
}

// Rótulos con el nombre de la clase y su rango. Sin rangos (ExG en análisis
// viejos, sin `umbrales` guardados) solo se muestran los nombres.
function etiquetasConRangos(umbrales) {
  const L = ETIQUETA_CLASE
  if (!Array.isArray(umbrales) || umbrales.length !== 3) {
    return { critica: L.critica, deficiente: L.deficiente, normal: L.normal, vigorosa: `${L.vigorosa} (umbral adaptativo por vuelo)` }
  }
  // con cortes chicos (< 0,1) dos decimales no distinguen las clases
  const decimales = Math.max(...umbrales.map(Math.abs)) < 0.1 ? 3 : 2
  const [u1, u2, u3] = umbrales.map((u) => u.toFixed(decimales))
  return {
    critica: `${L.critica} (< ${u1})`,
    deficiente: `${L.deficiente} (${u1}–${u2})`,
    normal: `${L.normal} (${u2}–${u3})`,
    vigorosa: `${L.vigorosa} (> ${u3})`,
  }
}

const ESTILO_LIMITE = { fill: false, color: '#7dd3fc', weight: 2, dashArray: '4 6' }

function styleFeature(feature) {
  const clase = feature?.properties?.clase
  return {
    fillColor: COLORES_CLASE[clase] ?? '#aaa',
    fillOpacity: 0.65,
    color: '#fff',
    weight: 1.2,
  }
}

function crearOnEachFeature(indiceLabel) {
  return function onEachFeature(feature, layer) {
    const p = feature?.properties
    if (!p) return
    const valor = p.ndvi_promedio != null ? p.ndvi_promedio.toFixed(3) : '–'
    const area = p.area_ha != null
      ? p.area_ha.toLocaleString('es-AR', { maximumFractionDigits: 1 })
      : '–'
    layer.bindTooltip(
      `<strong>${etiquetaClase(p.clase ?? 'zona')}</strong>` +
      `<br/>${indiceLabel} prom.: ${valor}` +
      `<br/>Área: ${area} ha`,
      { sticky: true, className: 'mapa-tooltip' }
    )
  }
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

const INDICE_LABEL = { ndvi: 'NDVI', ndre: 'NDRE', savi: 'SAVI', gndvi: 'GNDVI', exg: 'ExG' }

export default function MapaIndice({ geojson, indice = 'ndvi', limite = null }) {
  const nFeatures = geojson?.features?.length ?? 0
  const indiceLabel = INDICE_LABEL[indice] ?? indice.toUpperCase()
  // los cortes realmente usados vienen en el GeoJSON (con umbral adaptativo cambian por vuelo)
  const etiquetasClase = etiquetasConRangos(geojson?.umbrales ?? UMBRALES_FIJOS[indice])
  const onEachFeature = useMemo(() => crearOnEachFeature(indiceLabel), [indiceLabel])

  const bounds = useMemo(() => {
    // Sin ninguna zona (todo "sin datos") se encuadra el lote, no un mapa vacío.
    const geometrias = nFeatures
      ? geojson.features.map((f) => f.geometry)
      : [limite, geojson?.sin_datos].filter(Boolean)
    if (!geometrias.length) return null
    // Iterar con loop en lugar de spread+Math.min/max — el spread falla con stack
    // overflow cuando hay miles de polígonos con decenas de coordenadas cada uno.
    let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity
    for (const geometry of geometrias) {
      const type = geometry?.type
      const raw = geometry?.coordinates
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
  }, [geojson, nFeatures, limite])

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
        <PatronSinDatos />
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
          {geojson.sin_datos && (
            <GeoJSON
              key={`sin-datos-${JSON.stringify(geojson.sin_datos.coordinates?.[0]?.[0])}`}
              data={geojson.sin_datos}
              style={ESTILO_SIN_DATOS}
              onEachFeature={(_, layer) => layer.bindTooltip(TEXTO_SIN_DATOS, { sticky: true, className: 'mapa-tooltip' })}
            />
          )}
          <GeoJSON
            key={nFeatures}
            data={geojson}
            style={styleFeature}
            onEachFeature={onEachFeature}
          />
          {limite && (
            <GeoJSON
              key={`limite-${JSON.stringify(limite.coordinates?.[0]?.[0])}`}
              data={limite}
              style={ESTILO_LIMITE}
              interactive={false}
            />
          )}
          <InvalidarAlRedimensionar />
        </MapContainer>

        <div className="mapa-leyenda">
          <span className="leyenda-titulo">{indiceLabel}</span>
          {Object.entries(COLORES_CLASE).map(([clase, color]) => (
            <div key={clase} className="leyenda-item">
              <span className="leyenda-color" style={{ background: color }} />
              <span className="leyenda-label">{etiquetasClase[clase]}</span>
            </div>
          ))}
          {geojson.sin_datos && (
            <div className="leyenda-item">
              <span className="leyenda-color leyenda-color--sin-datos" />
              <span className="leyenda-label">Sin datos</span>
            </div>
          )}
        </div>
      </div>
    </MapaBoundary>
  )
}
