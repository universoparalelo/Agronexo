import { ETIQUETA_CLASE } from '../utils/clasesIndice'

const ORDEN = ['vigorosa', 'normal', 'deficiente', 'critica']

const ETIQUETAS = ETIQUETA_CLASE

const COLORES = {
  critica:    '#ef4444',
  deficiente: '#f97316',
  normal:     '#86efac',
  vigorosa:   '#16a34a',
}

export default function TablaZonas({ features }) {
  const stats = ORDEN.reduce((acc, clase) => {
    const zonas = features.filter(f => f.properties?.clase === clase)
    const area = zonas.reduce((s, f) => s + (f.properties?.area_ha || 0), 0)
    const ndviProm = zonas.length > 0
      ? zonas.reduce((s, f) => s + (f.properties?.ndvi_promedio || 0), 0) / zonas.length
      : null
    acc[clase] = { area, ndvi: ndviProm, poligonos: zonas.length }
    return acc
  }, {})

  const totalArea = Object.values(stats).reduce((s, c) => s + c.area, 0)

  return (
    <div className="tabla-zonas-wrapper">
      <h3 className="tabla-zonas-title">Distribución de zonas</h3>
      <table className="tabla-zonas">
        <thead>
          <tr>
            <th>Clase</th>
            <th>Área (ha)</th>
            <th>% del lote</th>
            <th>NDVI prom.</th>
            <th>Polígonos</th>
          </tr>
        </thead>
        <tbody>
          {ORDEN.map(clase => {
            const { area, ndvi, poligonos } = stats[clase]
            const pct = totalArea > 0 ? (area / totalArea * 100).toFixed(1) : '0.0'
            return (
              <tr key={clase}>
                <td>
                  <span className="clase-dot" style={{ background: COLORES[clase] }} />
                  {ETIQUETAS[clase]}
                </td>
                <td>{area.toFixed(2)}</td>
                <td>{pct}%</td>
                <td>{ndvi !== null ? ndvi.toFixed(3) : '—'}</td>
                <td>{poligonos}</td>
              </tr>
            )
          })}
          <tr className="tabla-total">
            <td><strong>Total</strong></td>
            <td><strong>{totalArea.toFixed(2)}</strong></td>
            <td><strong>100%</strong></td>
            <td>—</td>
            <td><strong>{features.length}</strong></td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
