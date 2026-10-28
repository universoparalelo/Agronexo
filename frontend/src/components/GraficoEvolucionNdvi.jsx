import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useEvolucionNdvi from '../hooks/useEvolucionNdvi'
import { explicarEvolucion, estadoVsEsperado, fechaVueloCorta } from '../utils/evolucionNdvi'

const ANCHO = 760
const ALTO = 240
const MARGEN = { top: 16, right: 24, bottom: 32, left: 40 }

// Umbrales generales de NDVI documentados para alertas automáticas (ver
// app/diagnostico/CLAUDE.md): <0.20 suelo desnudo, 0.20-0.70 en desarrollo
// o con estrés, >=0.70 vigor óptimo. Solo se pintan de fondo cuando la curva
// esperada está oculta — con la curva visible, la referencia es ella.
const BANDAS = [
  { desde: -0.2, hasta: 0.20, color: '#fee2e2' },
  { desde: 0.20, hasta: 0.70, color: '#fef9c3' },
  { desde: 0.70, hasta: 1.0,  color: '#dcfce7' },
]

const COLOR_REAL = '#27500a'
const COLOR_POR_ESTADO = { debajo: '#dc2626', normal: '#16a34a', encima: '#2563eb' }

// Línea de tiempo del NDVI real del lote (un punto por vuelo, eje X = fecha
// del vuelo) con superposición opcional del NDVI esperado para el estadio
// de cada vuelo y una explicación de la diferencia basada en los diagnósticos.
export default function GraficoEvolucionNdvi({ loteId, vuelos }) {
  const navigate = useNavigate()
  const { puntos, loading, error } = useEvolucionNdvi(loteId, vuelos)
  const [mostrarEsperado, setMostrarEsperado] = useState(true)

  if (loading) {
    return (
      <div className="grafico-evolucion grafico-evolucion--cargando">
        <span className="diagnostico-spinner" /> Calculando evolución de NDVI...
      </div>
    )
  }

  if (error) return <p className="empty-hint">{error}</p>
  if (puntos.length === 0) return null

  const comparables = puntos.filter(p => p.esperado)
  const verEsperado = mostrarEsperado && comparables.length > 0

  const fechaMin = new Date(puntos[0].fecha).getTime()
  const fechaMax = new Date(puntos[puntos.length - 1].fecha).getTime()
  const rangoFechas = fechaMax - fechaMin

  const valores = puntos.map(p => p.ndviProm)
  if (verEsperado) comparables.forEach(p => valores.push(p.esperado.min, p.esperado.max))
  const yDataMin = Math.min(...valores, 0.2)
  const yDataMax = Math.max(...valores, 0.7)
  const yPad = (yDataMax - yDataMin) * 0.12 || 0.05
  const yMin = Math.max(yDataMin - yPad, -0.2)
  const yMax = Math.min(yDataMax + yPad, 1.0)

  const innerW = ANCHO - MARGEN.left - MARGEN.right
  const innerH = ALTO - MARGEN.top - MARGEN.bottom

  const x = (fecha) => rangoFechas === 0
    ? MARGEN.left + innerW / 2
    : MARGEN.left + ((new Date(fecha).getTime() - fechaMin) / rangoFechas) * innerW
  const y = (ndvi) => MARGEN.top + innerH - ((ndvi - yMin) / (yMax - yMin)) * innerH

  const lineaPath = puntos.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(p.fecha).toFixed(1)} ${y(p.ndviProm).toFixed(1)}`).join(' ')

  const esperadoPath = comparables.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(p.fecha).toFixed(1)} ${y(p.esperado.valor).toFixed(1)}`).join(' ')
  const bandaPath = comparables.length > 1
    ? `M ${comparables.map(p => `${x(p.fecha).toFixed(1)} ${y(p.esperado.max).toFixed(1)}`).join(' L ')}` +
      ` L ${comparables.slice().reverse().map(p => `${x(p.fecha).toFixed(1)} ${y(p.esperado.min).toFixed(1)}`).join(' L ')} Z`
    : null

  // Ticks del eje X: primero, último y hasta 3 intermedios equiespaciados por índice.
  const maxTicks = 5
  const paso = Math.max(1, Math.ceil(puntos.length / maxTicks))
  const ticksX = puntos.filter((_, i) => i === 0 || i === puntos.length - 1 || i % paso === 0)

  const explicacion = explicarEvolucion(puntos)

  return (
    <div className="grafico-evolucion">
      <div className="grafico-evolucion-header">
        <h3 className="tabla-zonas-title">Evolución del NDVI</h3>
        <label className={`grafico-evolucion-toggle ${comparables.length === 0 ? 'grafico-evolucion-toggle--off' : ''}`}>
          <input
            type="checkbox"
            checked={verEsperado}
            disabled={comparables.length === 0}
            onChange={(e) => setMostrarEsperado(e.target.checked)}
          />
          Mostrar NDVI normal esperado
        </label>
      </div>

      <div className="tendencia-leyenda">
        <span><i className="tendencia-swatch" style={{ background: COLOR_REAL, height: 3 }} /> NDVI real del lote</span>
        {verEsperado && (
          <>
            <span><i className="tendencia-swatch tendencia-swatch--esperado" /> Esperado para la etapa</span>
            <span><i className="tendencia-swatch tendencia-swatch--banda" /> Rango normal</span>
            <span><i className="tendencia-swatch" style={{ background: COLOR_POR_ESTADO.debajo, borderRadius: '50%', width: 10 }} /> Por debajo de lo normal</span>
          </>
        )}
      </div>

      <svg
        viewBox={`0 0 ${ANCHO} ${ALTO}`}
        className="grafico-evolucion-svg"
        preserveAspectRatio="xMinYMin meet"
        role="img"
        aria-label="NDVI real del lote por fecha de vuelo comparado con el NDVI esperado"
      >
        {!verEsperado && BANDAS.map((b) => {
          const desde = Math.max(b.desde, yMin)
          const hasta = Math.min(b.hasta, yMax)
          if (hasta <= desde) return null
          return (
            <rect key={b.color} x={MARGEN.left} y={y(hasta)} width={innerW} height={y(desde) - y(hasta)} fill={b.color} />
          )
        })}

        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const valor = yMin + (yMax - yMin) * frac
          const yy = MARGEN.top + innerH * (1 - frac)
          return (
            <g key={frac}>
              <line x1={MARGEN.left} y1={yy} x2={ANCHO - MARGEN.right} y2={yy} stroke="#e5e7eb" strokeWidth="1" />
              <text x={MARGEN.left - 8} y={yy + 3} textAnchor="end" fontSize="9" fill="#6b7280">
                {valor.toFixed(2)}
              </text>
            </g>
          )
        })}

        {ticksX.map((p) => (
          <text key={p.vueloId} x={x(p.fecha)} y={ALTO - 8} textAnchor="middle" fontSize="9" fill="#6b7280">
            {fechaVueloCorta(p.fecha)}
          </text>
        ))}

        {verEsperado && (
          <g>
            {bandaPath && <path d={bandaPath} className="tendencia-banda" />}
            {comparables.length === 1 && (
              <line
                x1={x(comparables[0].fecha)} x2={x(comparables[0].fecha)}
                y1={y(comparables[0].esperado.min)} y2={y(comparables[0].esperado.max)}
                stroke="#d4ecd9" strokeWidth="10"
              />
            )}
            <path d={esperadoPath} className="tendencia-esperado" fill="none" />
            {comparables.map((p) => (
              <circle key={p.vueloId} cx={x(p.fecha)} cy={y(p.esperado.valor)} r="3.5" fill="#fff" stroke="#6b7280" strokeWidth="1.5">
                <title>{fechaVueloCorta(p.fecha)} · estadio {p.estadio} — NDVI esperado {p.esperado.valor.toFixed(2)} (normal {p.esperado.min.toFixed(2)}–{p.esperado.max.toFixed(2)})</title>
              </circle>
            ))}
          </g>
        )}

        {puntos.length > 1 && <path d={lineaPath} fill="none" stroke={COLOR_REAL} strokeWidth="2" />}

        {puntos.map((p) => {
          const estado = verEsperado ? estadoVsEsperado(p) : null
          return (
            <circle
              key={p.vueloId}
              cx={x(p.fecha)}
              cy={y(p.ndviProm)}
              r="4.5"
              fill={estado ? COLOR_POR_ESTADO[estado] : COLOR_REAL}
              stroke="#fff"
              strokeWidth="1.5"
              className="grafico-evolucion-punto"
              onClick={() => navigate(`/lotes/${loteId}/vuelos/${p.vueloId}`)}
            >
              <title>
                {fechaVueloCorta(p.fecha)}{p.estadio ? ` · estadio ${p.estadio}` : ''} — NDVI real {p.ndviProm.toFixed(3)}
                {p.esperado ? ` · esperado ${p.esperado.valor.toFixed(2)}` : ''}
                {p.ndviMin != null && p.ndviMax != null ? ` (zonas: mín ${p.ndviMin.toFixed(3)} / máx ${p.ndviMax.toFixed(3)})` : ''}
              </title>
            </circle>
          )
        })}
      </svg>

      <div className="grafico-evolucion-explicacion">
        <h4>¿Qué muestra la diferencia?</h4>
        {explicacion.map((texto, i) => <p key={i}>{texto}</p>)}
      </div>

      {comparables.length > 0 && (
        <p className="tendencia-nota">
          * El NDVI esperado sale de una curva de referencia genérica por cultivo y estadio, todavía no ajustada con datos reales — se refina a medida que se acumulan vuelos.
          {comparables.length < puntos.length && ` ${puntos.length - comparables.length} ${puntos.length - comparables.length === 1 ? 'vuelo no tiene' : 'vuelos no tienen'} estadio comparable con la curva.`}
        </p>
      )}
    </div>
  )
}
