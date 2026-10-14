import { useState, useEffect, useCallback, useRef } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import L from 'leaflet'
import { obtenerZonas, obtenerResultadoIndice } from '../api/analisis'

// Mismos colores que MapaIndice — la escala debe ser idéntica en todas las
// capas para que la comparación visual sea significativa.
const COLORES_CLASE = {
  critica:    '#c0392b',
  deficiente: '#e67e22',
  normal:     '#8fd16f',
  vigorosa:   '#1e8449',
}

const ETIQUETA_CLASE = {
  critica: 'Muy bajo',
  deficiente: 'Bajo',
  normal: 'Medio',
  vigorosa: 'Alto',
}

// Deben coincidir con workers/gis/clasificacion.py::_UMBRALES_POR_INDICE.
// Se ignoran los umbrales adaptativos del GeoJSON (otsu/percentil) para que
// la misma zona reciba el mismo color en todos los vuelos comparados.
const UMBRALES_FIJOS = {
  ndvi:  [0.20, 0.40, 0.70],
  gndvi: [0.25, 0.45, 0.60],
  ndre:  [0.10, 0.20, 0.35],
  savi:  [0.15, 0.30, 0.50],
  exg:   [0.05, 0.15, 0.30],
}

const INDICE_LABEL = { ndvi: 'NDVI', ndre: 'NDRE', savi: 'SAVI', gndvi: 'GNDVI', exg: 'ExG' }

// Clasifica un valor usando los umbrales fijos en lugar del campo `clase`
// del GeoJSON, que puede haber sido calculado con umbrales adaptativos.
function clasificar(valor, umbrales) {
  const [u1, u2, u3] = umbrales
  if (valor == null || isNaN(valor)) return 'normal'
  if (valor < u1) return 'critica'
  if (valor < u2) return 'deficiente'
  if (valor < u3) return 'normal'
  return 'vigorosa'
}

function calcularStats(geojson, indice) {
  if (!geojson?.features?.length) return null
  const umbrales = UMBRALES_FIJOS[indice] ?? UMBRALES_FIJOS.ndvi
  let sumPeso = 0, sumValor = 0
  const areaPorClase = { critica: 0, deficiente: 0, normal: 0, vigorosa: 0 }

  for (const f of geojson.features) {
    const area = f.properties?.area_ha ?? 0
    const valor = f.properties?.ndvi_promedio ?? 0
    const clase = clasificar(valor, umbrales)
    sumValor += valor * area
    sumPeso += area
    areaPorClase[clase] += area
  }

  const indice_medio = sumPeso > 0 ? sumValor / sumPeso : 0
  const area_total = sumPeso
  const pct = Object.fromEntries(
    Object.entries(areaPorClase).map(([k, v]) => [k, area_total > 0 ? (v / area_total) * 100 : 0])
  )
  return { indice_medio, area_total, areaPorClase, pct }
}

function fmtFecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function FitBounds({ capas }) {
  const map = useMap()
  // Las capas llegan async (fetchGeojson) — al montar, `capas` todavía no
  // tiene geojson (todo null), así que el ajuste tiene que esperar a que
  // los datos lleguen. yaAjustado evita repetir el fitBounds en cada
  // cambio posterior (toggle de visibilidad, etc.) y pelear con el pan/zoom
  // que el usuario haya hecho a mano.
  const yaAjustado = useRef(false)
  useEffect(() => {
    if (yaAjustado.current) return
    const geojsons = Object.values(capas)
      .filter(c => c.visible && c.geojson)
      .map(c => c.geojson)
    if (!geojsons.length) return
    try {
      const bounds = L.latLngBounds([])
      for (const g of geojsons) {
        const layer = L.geoJSON(g)
        const b = layer.getBounds()
        if (b.isValid()) bounds.extend(b)
      }
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [20, 20] })
        yaAjustado.current = true
      }
    } catch (_) {}
  }, [capas, map])
  return null
}

function AutoResize() {
  const map = useMap()
  useEffect(() => {
    const ro = new ResizeObserver(() => map.invalidateSize())
    ro.observe(map.getContainer())
    return () => ro.disconnect()
  }, [map])
  return null
}

// ── Panel de delta ─────────────────────────────────────────────────────────

function PanelDelta({ capasVisibles, indice }) {
  if (capasVisibles.length < 2) return null

  const ordenadas = [...capasVisibles].sort(
    (a, b) => new Date(a.fecha) - new Date(b.fecha)
  )
  const primera = ordenadas[0]
  const ultima  = ordenadas[ordenadas.length - 1]

  const statsA = calcularStats(primera.geojson, indice)
  const statsB = calcularStats(ultima.geojson, indice)
  if (!statsA || !statsB) return null

  const delta = statsB.indice_medio - statsA.indice_medio
  const signo = delta >= 0 ? '+' : ''
  const tendencia = delta > 0.05 ? 'mejora' : delta < -0.05 ? 'deterioro' : 'estable'
  const colorDelta = delta > 0.05 ? '#16a34a' : delta < -0.05 ? '#dc2626' : '#6b7280'

  return (
    <div className="mapa-capas-delta">
      <div className="delta-header">
        <span className="delta-titulo">Evolución {INDICE_LABEL[indice] ?? indice.toUpperCase()}</span>
        <span className="delta-fechas">{fmtFecha(primera.fecha)} → {fmtFecha(ultima.fecha)}</span>
      </div>

      <div className="delta-fila">
        <span className="delta-label">Valor medio</span>
        <span className="delta-valores">
          {statsA.indice_medio.toFixed(3)}
          {' → '}
          <strong>{statsB.indice_medio.toFixed(3)}</strong>
          {' '}
          <span style={{ color: colorDelta, fontWeight: 600 }}>
            ({signo}{delta.toFixed(3)})
          </span>
        </span>
      </div>

      <div className="delta-label" style={{ marginTop: '0.5rem', marginBottom: '0.25rem', fontSize: '0.75rem' }}>
        Distribución de superficie
      </div>
      {Object.keys(ETIQUETA_CLASE).map(clase => {
        const pA = statsA.pct[clase] ?? 0
        const pB = statsB.pct[clase] ?? 0
        const diff = pB - pA
        return (
          <div key={clase} className="delta-clase-fila">
            <span className="delta-clase-dot" style={{ background: COLORES_CLASE[clase] }} />
            <span className="delta-clase-nombre">{ETIQUETA_CLASE[clase]}</span>
            <span className="delta-clase-pct">{pA.toFixed(0)}%</span>
            <span className="delta-flecha">→</span>
            <span className="delta-clase-pct"><strong>{pB.toFixed(0)}%</strong></span>
            {Math.abs(diff) >= 2 && (
              <span style={{ color: diff > 0 ? (clase === 'vigorosa' || clase === 'normal' ? '#16a34a' : '#dc2626') : (clase === 'vigorosa' || clase === 'normal' ? '#dc2626' : '#16a34a'), fontSize: '0.72rem', marginLeft: '0.25rem' }}>
                {diff > 0 ? '▲' : '▼'}{Math.abs(diff).toFixed(0)}pp
              </span>
            )}
          </div>
        )
      })}

      <p className="delta-conclusion">
        {tendencia === 'mejora' && `Tendencia positiva — el lote mejoró en ${Math.abs(delta).toFixed(3)} unidades de ${INDICE_LABEL[indice] ?? indice.toUpperCase()} entre ambas fechas.`}
        {tendencia === 'deterioro' && `Tendencia negativa — el lote empeoró en ${Math.abs(delta).toFixed(3)} unidades de ${INDICE_LABEL[indice] ?? indice.toUpperCase()} entre ambas fechas.`}
        {tendencia === 'estable' && `Sin cambio significativo entre ambas fechas (Δ < 0.05).`}
      </p>
    </div>
  )
}

// ── Componente principal ───────────────────────────────────────────────────

export default function MapaCapas({ vuelos, indice = 'ndvi', limite }) {
  // vuelos: [{ vueloId, loteId, fecha }]
  const [capas, setCapas] = useState(() =>
    Object.fromEntries(vuelos.map(v => [v.vueloId, {
      ...v,
      geojson: null,
      visible: true,
      opacidad: 0.65,
      cargando: true,
      error: null,
    }]))
  )

  const fetchGeojson = useCallback(async (v) => {
    try {
      const data = indice === 'ndvi'
        ? await obtenerZonas(v.loteId, v.vueloId)
        : await obtenerResultadoIndice(v.loteId, v.vueloId, indice)
      setCapas(prev => ({
        ...prev,
        [v.vueloId]: { ...prev[v.vueloId], geojson: data, cargando: false },
      }))
    } catch {
      setCapas(prev => ({
        ...prev,
        [v.vueloId]: { ...prev[v.vueloId], cargando: false, error: 'No se pudo cargar' },
      }))
    }
  }, [indice])

  useEffect(() => {
    vuelos.forEach(v => fetchGeojson(v))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleVisible = (vueloId) =>
    setCapas(prev => ({ ...prev, [vueloId]: { ...prev[vueloId], visible: !prev[vueloId].visible } }))

  const setOpacidad = (vueloId, valor) =>
    setCapas(prev => ({ ...prev, [vueloId]: { ...prev[vueloId], opacidad: valor } }))

  const capasOrdenadas = Object.values(capas).sort((a, b) => new Date(a.fecha) - new Date(b.fecha))
  const capasVisibles  = capasOrdenadas.filter(c => c.visible && c.geojson)

  const umbrales = UMBRALES_FIJOS[indice] ?? UMBRALES_FIJOS.ndvi

  function estiloCapa(capa) {
    return (feature) => {
      const valor = feature.properties?.ndvi_promedio
      const clase = clasificar(valor, umbrales)
      return {
        fillColor: COLORES_CLASE[clase] ?? '#aaa',
        fillOpacity: capa.opacidad,
        color: '#fff',
        weight: 1.2,
      }
    }
  }

  function onEachFeature(indiceLabel) {
    return (feature, layer) => {
      const p = feature.properties || {}
      const valor = p.ndvi_promedio != null ? p.ndvi_promedio.toFixed(3) : '–'
      const area  = p.area_ha != null ? p.area_ha.toFixed(1) : '–'
      const clase = clasificar(p.ndvi_promedio, umbrales)
      layer.bindTooltip(
        `<strong>${ETIQUETA_CLASE[clase]}</strong><br/>${indiceLabel} prom.: ${valor}<br/>Área: ${area} ha`,
        { sticky: true, className: 'mapa-tooltip' }
      )
    }
  }

  const indiceLabel = INDICE_LABEL[indice] ?? indice.toUpperCase()
  const cargando    = capasOrdenadas.some(c => c.cargando)

  return (
    <div className="mapa-capas-root">
      {/* Panel de control de capas */}
      <div className="mapa-capas-panel">
        <div className="capas-panel-titulo">
          Capas — {indiceLabel}
          {cargando && <span className="capas-cargando">cargando…</span>}
        </div>
        <p className="capas-panel-ayuda">
          Cada fecha es una capa superpuesta en el mapa. Activá o desactivá cada una y ajustá su opacidad para comparar la evolución.
        </p>
        {capasOrdenadas.map((capa, idx) => (
          <div key={capa.vueloId} className="capa-fila">
            <label className="capa-toggle">
              <input
                type="checkbox"
                checked={capa.visible}
                onChange={() => toggleVisible(capa.vueloId)}
              />
              <span
                className="capa-color-swatch"
                style={{ opacity: capa.opacidad, borderLeft: `4px solid ${idx === 0 ? '#6366f1' : idx === 1 ? '#f59e0b' : '#10b981'}` }}
              />
              <span className="capa-fecha">{fmtFecha(capa.fecha)}</span>
              {capa.cargando && <span className="capa-badge">…</span>}
              {capa.error   && <span className="capa-badge capa-badge--error">!</span>}
            </label>
            {capa.visible && !capa.cargando && !capa.error && (
              <div className="capa-opacidad-fila">
                <span className="capa-opacidad-label">Opacidad</span>
                <input
                  type="range"
                  className="capa-opacidad"
                  min={0.1} max={1} step={0.05}
                  value={capa.opacidad}
                  onChange={e => setOpacidad(capa.vueloId, parseFloat(e.target.value))}
                  title="Opacidad de la capa"
                />
              </div>
            )}
          </div>
        ))}

        {/* Leyenda fija por índice */}
        <div className="capas-leyenda">
          <div className="capas-leyenda-titulo">Leyenda — {indiceLabel}</div>
          {Object.entries(ETIQUETA_CLASE).map(([clase, label]) => (
            <div key={clase} className="leyenda-item">
              <span className="leyenda-color" style={{ background: COLORES_CLASE[clase] }} />
              <span className="leyenda-label">{label}</span>
            </div>
          ))}
        </div>

        <PanelDelta capasVisibles={capasVisibles} indice={indice} />
      </div>

      {/* Mapa */}
      <div className="mapa-capas-map">
        <MapContainer
          center={[-27.47, -60.67]}
          zoom={13}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />
          <AutoResize />
          <FitBounds capas={capas} />

          {limite && (
            <GeoJSON
              key="limite"
              data={limite}
              style={{ fill: false, color: '#7dd3fc', weight: 2, dashArray: '4 6' }}
              interactive={false}
            />
          )}

          {capasVisibles.map(capa => (
            <GeoJSON
              key={`${capa.vueloId}-${capa.opacidad}`}
              data={capa.geojson}
              style={estiloCapa(capa)}
              onEachFeature={onEachFeature(indiceLabel)}
            />
          ))}
        </MapContainer>
      </div>
    </div>
  )
}
