import { useMemo } from 'react'
import {
  bboxDeGeometrias, crearProyector, emparejarZonas, pathSvgDeGeometria,
} from '../utils/cambioZonas'

const ANCHO_MAPA = 150
const ALTO_MAPA = 120

// Umbral para no marcar como "Empeoró"/"No empeoró" diferencias que son solo
// ruido de vectorización entre dos análisis independientes.
const UMBRAL_NDVI = 0.01

// Mismos labels que TablaDiagnostico.jsx/MapaZonas.jsx (no hay un util
// compartido todavía — se duplica con los mismos valores a propósito, mismo
// criterio que ya usan esos dos archivos entre sí).
const SEVERIDAD_COLORS = {
  critica:  'severidad-critica',
  moderada: 'severidad-moderada',
  leve:     'severidad-leve',
  normal:   'severidad-normal',
  vigorosa: 'severidad-vigorosa',
}
const SEVERIDAD_LABELS = {
  critica:  'Crítica',
  moderada: 'Moderada',
  leve:     'Leve',
  normal:   'Normal',
  vigorosa: 'Vigorosa',
}
const CAUSA_LABELS = {
  sin_problema_detectado: 'Sin problema',
  interferencia_vegetacion: 'Malezas',
  estres_biotico_fungico: 'Hongo',
  estres_biotico_insecto: 'Insecto',
  estres_nutricional_nitrogeno: 'Déficit N',
  estres_nutricional_micro: 'Déficit micro',
  estres_nutricional_fosforo: 'Déficit P',
  estres_hidrico: 'Estrés hídrico',
  madurez_temprana_diferencial: 'Madurez dif.',
  vigor_excesivo: 'Vigor excesivo',
  compactacion_falla_siembra: 'Compactación / siembra',
  bajo_vigor_estadio: 'Vigor bajo p/ estadio',
}

function MiniSilueta({ lotePath, zonaPath, color }) {
  return (
    <svg
      className="cambio-zona-svg"
      viewBox={`0 0 ${ANCHO_MAPA} ${ALTO_MAPA}`}
      width={ANCHO_MAPA}
      height={ALTO_MAPA}
      role="img"
      aria-label="Ubicación de la zona dentro del lote"
    >
      {lotePath && <path d={lotePath} className="cambio-zona-svg-lote" />}
      <path d={zonaPath} fill={color} className="cambio-zona-svg-zona" />
    </svg>
  )
}

function textoNdvi(delta) {
  if (delta == null) return 'Sin dato previo en esta posición'
  if (Math.abs(delta) < UMBRAL_NDVI) return `NDVI estable (${delta >= 0 ? '+' : ''}${delta.toFixed(3)})`
  return delta < 0 ? `NDVI bajó ${Math.abs(delta).toFixed(3)}` : `NDVI subió ${delta.toFixed(3)}`
}

// Por cada zona del vuelo A (el que se estaba viendo), busca la misma
// posición en el vuelo B y muestra solo si empeoró o no — simplificado a
// propósito respecto del cambio de clase, que ya se ve en la tabla de arriba.
// El diagnóstico (causa + severidad + texto) es el de ESE vuelo A para esa
// zona puntual — no hay un "diagnóstico de la diferencia", cada zona puede
// tener una causa distinta de la otra.
export default function CambioPorZona({ lote, featuresA = [], featuresB = [], diagnosticoFeatures = [] }) {
  const pares = useMemo(() => emparejarZonas(featuresA, featuresB), [featuresA, featuresB])

  // diagnosticoFeatures viene del mismo GeoJSON de NDVI (mismo orden/índice,
  // ver app/diagnostico/service.py::_calcular_diagnostico) — se mapea por
  // posición en vez de por una propiedad compartida porque las features
  // "crudas" de featuresA no traen zona_id, solo las ya enriquecidas sí.
  const diagnosticoPorZona = useMemo(
    () => new Map(featuresA.map((f, i) => [f, diagnosticoFeatures[i]])),
    [featuresA, diagnosticoFeatures],
  )

  const bbox = useMemo(() => {
    const geometrias = lote?.geometry
      ? [lote.geometry]
      : [...featuresA, ...featuresB].map((f) => f.geometry)
    return bboxDeGeometrias(geometrias)
  }, [lote, featuresA, featuresB])

  if (pares.length === 0 || !bbox) return null

  const proyectar = crearProyector(bbox, ANCHO_MAPA, ALTO_MAPA)
  const lotePath = lote?.geometry ? pathSvgDeGeometria(lote.geometry, proyectar) : null
  const areaLote = pares.reduce((s, { zona }) => s + (zona.properties?.area_ha || 0), 0)

  return (
    <div className="cambio-zona">
      <div className="resumen-diferencia-encabezado">
        <h3>Cambio por zona</h3>
        <span className="resumen-diferencia-fechas">Ordenadas de mayor a menor superficie</span>
      </div>

      <div className="cambio-zona-grid">
        {pares.map(({ zona, match, deltaNdvi }, i) => {
          const empeoro = deltaNdvi != null && deltaNdvi < -UMBRAL_NDVI
          const noEmpeoro = deltaNdvi != null && deltaNdvi >= -UMBRAL_NDVI
          const color = !match ? '#9ca3af' : empeoro ? '#ef4444' : '#16a34a'
          const area = zona.properties?.area_ha || 0
          const pct = areaLote > 0 ? (area / areaLote) * 100 : 0
          const diag = diagnosticoPorZona.get(zona)?.properties

          return (
            <div key={zona.properties?.zona_id ?? i} className="cambio-zona-card">
              <div className="cambio-zona-mapa">
                <MiniSilueta lotePath={lotePath} zonaPath={pathSvgDeGeometria(zona.geometry, proyectar)} color={color} />
              </div>

              <div className="cambio-zona-info">
                <div className="cambio-zona-titulo-fila">
                  <strong>Zona {i + 1}</strong>
                  {!match && <span className="cambio-zona-badge cambio-zona-badge--neutro">Sin comparar</span>}
                  {empeoro && <span className="cambio-zona-badge cambio-zona-badge--mal">▼ Empeoró</span>}
                  {noEmpeoro && <span className="cambio-zona-badge cambio-zona-badge--bien">No empeoró</span>}
                </div>
                <p className="cambio-zona-ndvi">{textoNdvi(deltaNdvi)}</p>
                <p className="cambio-zona-area">{area.toFixed(2)} ha · {pct.toFixed(0)}% del lote</p>
              </div>

              <div className="cambio-zona-razones">
                <span className="cambio-zona-razones-titulo">Diagnóstico</span>
                {!diag && <p className="cambio-zona-razones-vacio">Sin diagnóstico disponible</p>}
                {diag && (
                  <>
                    <div className="cambio-zona-diagnostico-fila">
                      <span className={`diagnostico-badge ${SEVERIDAD_COLORS[diag.severidad] || ''}`}>
                        {SEVERIDAD_LABELS[diag.severidad] || diag.severidad}
                      </span>
                      <strong>{CAUSA_LABELS[diag.causa_indice] || diag.causa_indice}</strong>
                    </div>
                    {diag.accion_recomendada && diag.regla_id !== 'R99' && (
                      <p className="cambio-zona-diagnostico-texto">{diag.accion_recomendada.split('. ')[0].replace(/\.$/, '')}.</p>
                    )}
                  </>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
