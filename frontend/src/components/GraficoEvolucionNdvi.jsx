import { useNavigate } from 'react-router-dom'
import useEvolucionNdvi from '../hooks/useEvolucionNdvi'

const ANCHO = 760
const ALTO = 220
const MARGEN = { top: 16, right: 20, bottom: 32, left: 40 }

// Umbrales generales de NDVI documentados para alertas automáticas (ver
// CLAUDE.md): <0.20 suelo desnudo, 0.20-0.70 cultivo en desarrollo/con
// estrés, >=0.70 vigor óptimo. Se usan acá solo como franjas de fondo de
// referencia visual, no reclasifican los puntos.
const BANDAS = [
  { desde: -0.2, hasta: 0.20, color: '#fee2e2' },
  { desde: 0.20, hasta: 0.70, color: '#fef9c3' },
  { desde: 0.70, hasta: 1.0,  color: '#dcfce7' },
]

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short' })
}

// Línea de tiempo del NDVI promedio del lote: un punto por vuelo completado,
// para ver de un vistazo cuándo mejoró o empeoró el cultivo en la campaña.
// Complementa al rango min/prom/máx de un único vuelo (ResumenVuelo) con la
// evolución entre vuelos.
export default function GraficoEvolucionNdvi({ loteId, vuelos }) {
  const navigate = useNavigate()
  const { puntos, loading, error } = useEvolucionNdvi(loteId, vuelos)

  if (loading) {
    return (
      <div className="grafico-evolucion grafico-evolucion--cargando">
        <span className="diagnostico-spinner" /> Calculando evolución de NDVI...
      </div>
    )
  }

  if (error) return <p className="empty-hint">{error}</p>
  if (puntos.length === 0) return null

  if (puntos.length === 1) {
    const p = puntos[0]
    return (
      <div className="grafico-evolucion">
        <h3 className="tabla-zonas-title">Evolución del NDVI</h3>
        <p className="empty-hint">
          Todavía hay un solo vuelo completado ({fechaCorta(p.fecha)}, NDVI {p.ndviProm.toFixed(3)}) —
          la línea de tiempo se arma a partir del segundo.
        </p>
      </div>
    )
  }

  const fechaMin = new Date(puntos[0].fecha).getTime()
  const fechaMax = new Date(puntos[puntos.length - 1].fecha).getTime()
  const rangoFechas = Math.max(fechaMax - fechaMin, 1)

  const valores = puntos.map(p => p.ndviProm)
  const yDataMin = Math.min(...valores, 0.2)
  const yDataMax = Math.max(...valores, 0.7)
  const yPad = (yDataMax - yDataMin) * 0.15 || 0.05
  const yMin = Math.max(yDataMin - yPad, -0.2)
  const yMax = Math.min(yDataMax + yPad, 1.0)

  const innerW = ANCHO - MARGEN.left - MARGEN.right
  const innerH = ALTO - MARGEN.top - MARGEN.bottom

  const x = (fecha) => MARGEN.left + ((new Date(fecha).getTime() - fechaMin) / rangoFechas) * innerW
  const y = (ndvi) => MARGEN.top + innerH - ((ndvi - yMin) / (yMax - yMin)) * innerH

  const lineaPath = puntos.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(p.fecha).toFixed(1)} ${y(p.ndviProm).toFixed(1)}`).join(' ')

  // Ticks del eje X: primero, último y hasta 3 intermedios equiespaciados por índice.
  const maxTicks = 5
  const paso = Math.max(1, Math.ceil(puntos.length / maxTicks))
  const ticksX = puntos.filter((_, i) => i === 0 || i === puntos.length - 1 || i % paso === 0)

  return (
    <div className="grafico-evolucion">
      <h3 className="tabla-zonas-title">Evolución del NDVI</h3>
      <svg
        viewBox={`0 0 ${ANCHO} ${ALTO}`}
        className="grafico-evolucion-svg"
        preserveAspectRatio="xMinYMin meet"
      >
        {BANDAS.map((b) => {
          const desde = Math.max(b.desde, yMin)
          const hasta = Math.min(b.hasta, yMax)
          if (hasta <= desde) return null
          return (
            <rect
              key={b.color}
              x={MARGEN.left}
              y={y(hasta)}
              width={innerW}
              height={y(desde) - y(hasta)}
              fill={b.color}
            />
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
            {fechaCorta(p.fecha)}
          </text>
        ))}

        <path d={lineaPath} fill="none" stroke="#27500a" strokeWidth="2" />

        {puntos.map((p) => (
          <circle
            key={p.vueloId}
            cx={x(p.fecha)}
            cy={y(p.ndviProm)}
            r="4"
            fill="#27500a"
            stroke="#fff"
            strokeWidth="1.5"
            className="grafico-evolucion-punto"
            onClick={() => navigate(`/lotes/${loteId}/vuelos/${p.vueloId}`)}
          >
            <title>
              {fechaCorta(p.fecha)}{p.estadio ? ` · estadio ${p.estadio}` : ''} — NDVI prom. {p.ndviProm.toFixed(3)}
              {p.ndviMin != null && p.ndviMax != null ? ` (mín ${p.ndviMin.toFixed(3)} / máx ${p.ndviMax.toFixed(3)})` : ''}
            </title>
          </circle>
        ))}
      </svg>
    </div>
  )
}
