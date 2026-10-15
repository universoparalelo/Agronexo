import { ETIQUETA_CLASE } from '../utils/clasesIndice'
import { ORDEN_CLASES, calcularStatsZonas } from '../utils/statsZonas'
import CambioPorZona from './CambioPorZona'
import TendenciaIndice from './TendenciaIndice'

const COLORES = {
  critica:    '#ef4444',
  deficiente: '#f97316',
  normal:     '#86efac',
  vigorosa:   '#16a34a',
}

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function Delta({ valor, decimales = 2, sufijo = '' }) {
  if (valor === null) return <span className="delta delta--neutro">—</span>
  const signo = valor > 0 ? '+' : ''
  const clase = valor > 0 ? 'delta--positivo' : valor < 0 ? 'delta--negativo' : 'delta--neutro'
  return <span className={`delta ${clase}`}>{signo}{valor.toFixed(decimales)}{sufijo}</span>
}

// Diferencia de valor medio del índice y de superficie por severidad entre
// dos vuelos del mismo lote (HU-R4-09). Vuelo A = el que estaba abierto antes
// de elegir "Seleccionar para comparar"; vuelo B = el elegido. El delta
// siempre es B − A, sin asumir cuál de los dos es más reciente.
export default function ResumenDiferenciaVuelos({ vueloA, vueloB, featuresA, featuresB, diagnosticoA, lote }) {
  const statsA = calcularStatsZonas(featuresA)
  const statsB = calcularStatsZonas(featuresB)

  const deltaNdviGeneral = statsA.ndviPromedioGeneral != null && statsB.ndviPromedioGeneral != null
    ? statsB.ndviPromedioGeneral - statsA.ndviPromedioGeneral
    : null

  return (
    <div className="resumen-diferencia">
      <div className="resumen-diferencia-fila">
        <div className="resumen-diferencia-col">
          <div className="resumen-diferencia-encabezado">
            <h3>Diferencia entre vuelos</h3>
            <span className="resumen-diferencia-fechas">
              {fechaCorta(vueloA.fecha_vuelo)} <strong>→</strong> {fechaCorta(vueloB.fecha_vuelo)}
            </span>
          </div>

          <div className="resumen-diferencia-general">
            <span>Índice promedio del lote</span>
            <span>{statsA.ndviPromedioGeneral?.toFixed(3) ?? '—'}</span>
            <strong>→</strong>
            <span>{statsB.ndviPromedioGeneral?.toFixed(3) ?? '—'}</span>
            <Delta valor={deltaNdviGeneral} decimales={3} />
          </div>

          <table className="tabla-zonas resumen-diferencia-tabla">
            <thead>
              <tr>
                <th>Clase</th>
                <th>Área A (ha)</th>
                <th>Área B (ha)</th>
                <th>Δ área (ha)</th>
              </tr>
            </thead>
            <tbody>
              {ORDEN_CLASES.map(clase => {
                const areaA = statsA.porClase[clase].area
                const areaB = statsB.porClase[clase].area
                return (
                  <tr key={clase}>
                    <td>
                      <span className="clase-dot" style={{ background: COLORES[clase] }} />
                      {ETIQUETA_CLASE[clase]}
                    </td>
                    <td>{areaA.toFixed(2)}</td>
                    <td>{areaB.toFixed(2)}</td>
                    <td><Delta valor={areaB - areaA} /></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="resumen-diferencia-col">
          <TendenciaIndice
            vueloA={vueloA} vueloB={vueloB}
            ndviRealA={statsA.ndviPromedioGeneral} ndviRealB={statsB.ndviPromedioGeneral}
          />
        </div>
      </div>

      <CambioPorZona
        lote={lote} featuresA={featuresA} featuresB={featuresB}
        diagnosticoFeatures={diagnosticoA?.features || []}
      />
    </div>
  )
}
