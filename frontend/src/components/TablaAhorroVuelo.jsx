function fmtNum(valor, decimales = 2) {
  if (valor == null) return '—'
  return valor.toLocaleString('es-AR', { minimumFractionDigits: decimales, maximumFractionDigits: decimales })
}

function fmtUsd(valor) {
  return valor == null ? '—' : `US$ ${fmtNum(valor, 2)}`
}

// Ahorro de UN vuelo: aplicar el producto solo donde hace falta (la orden de
// trabajo del sistema) contra aplicarlo en todo el lote.
export default function TablaAhorroVuelo({ ahorro, onCargarPrecio }) {
  const productos = ahorro.productos || []

  return (
    <div className="ahorro-vuelo">
      <div className="seccion-encabezado">
        <h3 className="tabla-zonas-title">Ahorro por aplicación selectiva</h3>
        <p className="seccion-sub">
          Cuánto producto y cuánto dinero se ahorra aplicando solo donde hace falta, según nuestra orden de trabajo,
          en lugar de aplicarlo en todo el lote.
        </p>
      </div>

      {productos.length === 0 ? (
        <p className="empty-hint">Este vuelo no tiene zonas para tratar: no hay nada que comparar.</p>
      ) : (
        <>
          <div className="ahorro-vuelo-resumen">
            <div>
              <span>Superficie tratada</span>
              <strong>{fmtNum(ahorro.area_tratada_ha, 1)} ha</strong>
            </div>
            <div>
              <span>Superficie del lote</span>
              <strong>{fmtNum(ahorro.area_total_lote_ha, 1)} ha</strong>
            </div>
            <div>
              <span>Ahorro total estimado</span>
              <strong>{fmtUsd(ahorro.ahorro_total_pesos)}</strong>
            </div>
          </div>

          {!ahorro.todos_los_precios_cargados && (
            <p className="ahorro-aviso-parcial">
              El total es parcial: falta el precio de algún producto (marcado en la tabla).
            </p>
          )}

          <table className="tabla-zonas">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Solo donde hace falta</th>
                <th>En todo el lote</th>
                <th>Ahorro</th>
                <th>Ahorro %</th>
                <th>Ahorro US$</th>
              </tr>
            </thead>
            <tbody>
              {productos.map((p) => (
                <tr key={p.producto}>
                  <td>{p.producto}</td>
                  <td>{fmtNum(p.cantidad_variable)} {p.unidad_dosis}</td>
                  <td>{p.cantidad_uniforme == null ? '—' : `${fmtNum(p.cantidad_uniforme)} ${p.unidad_dosis ?? ''}`}</td>
                  <td>{fmtNum(p.ahorro_cantidad)}</td>
                  <td>{p.ahorro_pct != null ? `${fmtNum(p.ahorro_pct, 0)}%` : '—'}</td>
                  <td>
                    {p.ahorro_pesos != null
                      ? fmtUsd(p.ahorro_pesos)
                      : (p.producto_id
                        ? <button type="button" className="card-link" onClick={() => onCargarPrecio(p.producto_id, p.producto, p.unidad_dosis)}>Cargar precio</button>
                        : '—')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
