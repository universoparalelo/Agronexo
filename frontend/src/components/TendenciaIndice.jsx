import { useEffect, useState } from 'react'
import { obtenerNdviEsperado } from '../api/analisis'
import { buscarPuntoPorEstadio } from '../utils/estadios'
import { etiquetaTipoCultivo } from '../utils/cultivos'

const ANCHO = 560
const ALTO = 220
const MARGEN = { top: 16, right: 16, bottom: 34, left: 34 }
const COLOR_DESVIO_MAL = '#ef4444'
const COLOR_DESVIO_BIEN = '#16a34a'

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short' })
}

function Delta({ valor }) {
  if (valor == null) return '—'
  const signo = valor > 0 ? '+' : ''
  return `${signo}${valor.toFixed(2)}`
}

// Compara la tendencia real del lote (entre los dos vuelos elegidos) contra
// la curva placeholder de NDVI esperado por estadio (migración 0025 —
// "se actualizará cuando haya suficientes ejemplos de vuelos", no es
// una curva agronómica validada todavía). Solo se dibuja si ambos vuelos son
// del mismo cultivo y tienen un estadio fenológico cargado que matchea la
// curva — si falta algo, no se aporta información confiable y no se muestra.
export default function TendenciaIndice({ vueloA, vueloB, ndviRealA, ndviRealB }) {
  const [curva, setCurva] = useState(null)
  const [error, setError] = useState(false)

  const cultivo = vueloA?.cultivo?.tipo_cultivo
  const mismoCultivo = cultivo && cultivo === vueloB?.cultivo?.tipo_cultivo

  useEffect(() => {
    if (!mismoCultivo) return
    let cancelado = false
    obtenerNdviEsperado(cultivo)
      .then((data) => { if (!cancelado) setCurva(data.puntos) })
      .catch(() => { if (!cancelado) setError(true) })
    return () => { cancelado = true }
  }, [cultivo, mismoCultivo])

  if (!mismoCultivo || !curva || error) return null

  // Orden cronológico real, independiente de cuál se abrió primero.
  const [vueloAnterior, vueloActual] = new Date(vueloA.fecha_vuelo) <= new Date(vueloB.fecha_vuelo)
    ? [vueloA, vueloB] : [vueloB, vueloA]
  const [ndviAnterior, ndviActual] = vueloAnterior === vueloA ? [ndviRealA, ndviRealB] : [ndviRealB, ndviRealA]

  const puntoAnterior = buscarPuntoPorEstadio(curva, vueloAnterior.estadio_fenologico)
  const puntoActual = buscarPuntoPorEstadio(curva, vueloActual.estadio_fenologico)
  if (!puntoAnterior || !puntoActual || ndviAnterior == null || ndviActual == null) return null

  const cambioEsperado = puntoActual.ndvi_esperado - puntoAnterior.ndvi_esperado
  const cambioReal = ndviActual - ndviAnterior
  const desvio = cambioReal - cambioEsperado
  const colorReal = desvio < 0 ? COLOR_DESVIO_MAL : COLOR_DESVIO_BIEN

  const minOrden = curva[0].orden
  const maxOrden = curva[curva.length - 1].orden
  const anchoUtil = ANCHO - MARGEN.left - MARGEN.right
  const altoUtil = ALTO - MARGEN.top - MARGEN.bottom

  const x = (orden) => MARGEN.left + (maxOrden === minOrden ? 0 : ((orden - minOrden) / (maxOrden - minOrden)) * anchoUtil)
  const y = (ndvi) => MARGEN.top + (1 - Math.max(0, Math.min(1, ndvi))) * altoUtil

  const bandaArriba = curva.map((p) => `${x(p.orden)},${y(p.ndvi_max)}`).join('L')
  const bandaAbajo = curva.slice().reverse().map((p) => `${x(p.orden)},${y(p.ndvi_min)}`).join('L')
  const bandaPath = `M${bandaArriba}L${bandaAbajo}Z`
  const esperadoPath = `M${curva.map((p) => `${x(p.orden)},${y(p.ndvi_esperado)}`).join('L')}`

  const pAnt = [x(puntoAnterior.orden), y(ndviAnterior)]
  const pAct = [x(puntoActual.orden), y(ndviActual)]
  const yEsperadoEnActual = y(puntoActual.ndvi_esperado)

  const ticksY = [0, 0.25, 0.5, 0.75, 1]

  return (
    <div className="tendencia-indice">
      <div className="resumen-diferencia-encabezado">
        <h3>Tendencia del índice</h3>
        <span className="resumen-diferencia-fechas">
          Lo real del lote contra lo esperado para su etapa ({etiquetaTipoCultivo(cultivo)})
        </span>
      </div>

      <div className="tendencia-leyenda">
        <span><i className="tendencia-swatch tendencia-swatch--banda" /> Rango normal para el {etiquetaTipoCultivo(cultivo).toLowerCase()}</span>
        <span><i className="tendencia-swatch tendencia-swatch--esperado" /> Esperado</span>
        <span><i className="tendencia-swatch" style={{ background: colorReal }} /> Lote (real)</span>
      </div>

      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="tendencia-svg" role="img" aria-label="Tendencia del NDVI real contra lo esperado">
        {ticksY.map((t) => (
          <g key={t}>
            <line x1={MARGEN.left} x2={ANCHO - MARGEN.right} y1={y(t)} y2={y(t)} className="tendencia-grid" />
            <text x={MARGEN.left - 8} y={y(t)} className="tendencia-tick" textAnchor="end" dominantBaseline="middle">{t.toLocaleString('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 2 })}</text>
          </g>
        ))}

        <path d={bandaPath} className="tendencia-banda" />
        <path d={esperadoPath} className="tendencia-esperado" fill="none" />

        <line x1={pAct[0]} x2={pAct[0]} y1={pAct[1]} y2={yEsperadoEnActual} className="tendencia-desvio-linea" />

        <line x1={pAnt[0]} y1={pAnt[1]} x2={pAct[0]} y2={pAct[1]} stroke={colorReal} strokeWidth="2" />
        <circle cx={pAnt[0]} cy={pAnt[1]} r="5" fill="#fff" stroke={colorReal} strokeWidth="2" />
        <circle cx={pAct[0]} cy={pAct[1]} r="5" fill={colorReal} />

        <text x={pAnt[0] - 8} y={pAnt[1] - 10} className="tendencia-valor" textAnchor="end">{ndviAnterior.toFixed(3)}</text>
        <text x={pAct[0] + 8} y={pAct[1] - 10} className="tendencia-valor" textAnchor="start">{ndviActual.toFixed(3)}</text>
        <text
          x={pAct[0]} y={Math.min(pAct[1], yEsperadoEnActual) - 18}
          className="tendencia-desvio-texto"
          textAnchor={pAct[0] > ANCHO / 2 ? 'end' : 'start'}
        >
          {desvio >= 0 ? '+' : ''}{desvio.toFixed(2)} vs. esperado
        </text>

        {/* Ancladas hacia afuera (no centradas) para no superponerse cuando
            los dos estadios comparados quedan cerca en el eje X. */}
        <text x={pAnt[0] - 6} y={ALTO - 10} className="tendencia-eje-x" textAnchor="end">{fechaCorta(vueloAnterior.fecha_vuelo)} · {puntoAnterior.estadio}</text>
        <text x={pAct[0] + 6} y={ALTO - 10} className="tendencia-eje-x" textAnchor="start">{fechaCorta(vueloActual.fecha_vuelo)} · {puntoActual.estadio}</text>
      </svg>

      <div className="tendencia-stats">
        <div className="tendencia-stat">
          <span className="tendencia-stat-titulo">Cambio esperado</span>
          <span className="tendencia-stat-valor"><Delta valor={cambioEsperado} /></span>
        </div>
        <div className="tendencia-stat">
          <span className="tendencia-stat-titulo">Cambio real</span>
          <span className="tendencia-stat-valor"><Delta valor={cambioReal} /></span>
        </div>
        <div className={`tendencia-stat tendencia-stat--desvio ${desvio < 0 ? 'tendencia-stat--mal' : 'tendencia-stat--bien'}`}>
          <span className="tendencia-stat-titulo">Desvío</span>
          <span className="tendencia-stat-valor"><Delta valor={desvio} /></span>
        </div>
      </div>

      <p className="tendencia-nota">
        * Curva de referencia genérica por estadio, todavía no ajustada con datos reales del cultivo — se refina a medida que se acumulan vuelos.
      </p>
    </div>
  )
}
