import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import client from '../api/client'
import { obtenerAhorroComparativo } from '../api/ahorro'
import { descripcionCultivo } from '../utils/cultivos'
import PanelLayout from '../components/PanelLayout'
import ModalCargarPrecio from '../components/ModalCargarPrecio'

function fmtNum(valor, decimales = 1) {
  if (valor == null) return '—'
  return valor.toLocaleString('es-AR', { minimumFractionDigits: decimales, maximumFractionDigits: decimales })
}

function fmtPesos(valor) {
  if (valor == null) return '—'
  return `US$ ${valor.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function Delta({ valor, formatear = fmtNum }) {
  if (valor == null) return <span className="delta delta--neutro">—</span>
  const signo = valor > 0 ? '+' : ''
  const clase = valor > 0 ? 'delta--positivo' : valor < 0 ? 'delta--negativo' : 'delta--neutro'
  return <span className={`delta ${clase}`}>{signo}{formatear(valor)}</span>
}

function CampanaAhorro({ titulo, campana, onCargarPrecio }) {
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">{titulo}</div>
          <div className="card-sub">
            {campana.n_vuelos_considerados} vuelo{campana.n_vuelos_considerados === 1 ? '' : 's'} con diagnóstico
            {campana.n_vuelos_sin_diagnostico > 0 && ` · ${campana.n_vuelos_sin_diagnostico} sin diagnóstico disponible`}
          </div>
        </div>
        <div className="card-title">{fmtPesos(campana.ahorro_total_pesos)}</div>
      </div>
      <div className="card-body">
        {!campana.todos_los_precios_cargados && (
          <p className="ahorro-aviso-parcial">
            El total es parcial — falta cargar el precio de algún producto (marcado abajo).
          </p>
        )}

        {campana.productos.length === 0 ? (
          <p className="empty-hint">Sin unidades de manejo tratadas en esta campaña — nada que comparar.</p>
        ) : (
          <table className="tabla-zonas">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Variable</th>
                <th>Uniforme</th>
                <th>Ahorro</th>
                <th>Ahorro %</th>
                <th>Ahorro US$</th>
              </tr>
            </thead>
            <tbody>
              {campana.productos.map((p) => (
                <tr key={p.producto}>
                  <td>{p.producto}</td>
                  <td>{fmtNum(p.cantidad_variable, 2)} {p.unidad_dosis}</td>
                  <td>{p.sin_dosis_referencia ? '—' : `${fmtNum(p.cantidad_uniforme, 2)} ${p.unidad_dosis ?? ''}`}</td>
                  <td>{p.sin_dosis_referencia ? '—' : fmtNum(p.ahorro_cantidad, 2)}</td>
                  <td>{p.ahorro_pct != null ? `${fmtNum(p.ahorro_pct, 0)}%` : '—'}</td>
                  <td>
                    {p.sin_precio
                      ? (p.producto_id
                        ? <button type="button" className="card-link" onClick={() => onCargarPrecio(p.producto_id, p.producto, p.unidad_dosis)}>Cargar precio</button>
                        : '—')
                      : fmtPesos(p.ahorro_pesos)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default function AhorroComparativo() {
  const { loteId } = useParams()
  const [lote, setLote] = useState(null)
  const [cultivoA, setCultivoA] = useState('')
  const [cultivoB, setCultivoB] = useState('')
  const [resultado, setResultado] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [precioForm, setPrecioForm] = useState(null) // { productoId, nombre, unidad } | null

  useEffect(() => {
    client.get(`/lotes/${loteId}`).then((r) => {
      setLote(r.data)
      if (r.data.cultivos?.length) setCultivoA(r.data.cultivos[0].id)
    })
  }, [loteId])

  const calcular = useCallback(() => {
    if (!cultivoA) return
    setCargando(true)
    setError('')
    obtenerAhorroComparativo(loteId, cultivoA, cultivoB || null)
      .then(setResultado)
      .catch((err) => setError(err.response?.data?.detail || 'No se pudo calcular el ahorro comparativo.'))
      .finally(() => setCargando(false))
  }, [loteId, cultivoA, cultivoB])

  useEffect(() => { calcular() }, [calcular])

  if (!lote) return <div className="page-loading">Cargando lote...</div>

  const cultivos = lote.cultivos ?? []
  const deltaAhorro = resultado?.campana_b
    ? resultado.campana_b.ahorro_total_pesos - resultado.campana_a.ahorro_total_pesos
    : null

  return (
    <PanelLayout
      migas={[
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Lotes', to: '/lotes' },
        { label: lote.nombre, to: `/lotes/${loteId}` },
        { label: 'Ahorro comparativo' },
      ]}
    >
      <main className="detalle-main">
        <div className="pagina-encabezado">
          <h1>Ahorro comparativo</h1>
          <span className="pagina-encabezado-meta">{lote.nombre} · {fmtNum(lote.area_ha, 1)} ha</span>
        </div>

        {cultivos.length === 0 ? (
          <div className="empty-state">
            <p>Este lote todavía no tiene cultivos cargados.</p>
            <p className="empty-hint">El ahorro se calcula por campaña — cargá un cultivo desde el modal de análisis.</p>
          </div>
        ) : (
          <>
            <div className="card">
              <div className="card-body perfil-card-body">
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="cultivo_a">Campaña</label>
                    <select id="cultivo_a" value={cultivoA} onChange={(e) => setCultivoA(e.target.value)}>
                      {cultivos.map((c) => (
                        <option key={c.id} value={c.id}>{descripcionCultivo(c)}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="cultivo_b">Comparar contra <span className="label-opcional">(opcional)</span></label>
                    <select id="cultivo_b" value={cultivoB} onChange={(e) => setCultivoB(e.target.value)}>
                      <option value="">Sin comparar</option>
                      {cultivos.filter((c) => c.id !== cultivoA).map((c) => (
                        <option key={c.id} value={c.id}>{descripcionCultivo(c)}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            </div>

            {error && <p className="error-message">{error}</p>}
            {cargando && <p className="empty-hint">Calculando ahorro...</p>}

            {resultado && !cargando && (
              <>
                {resultado.campana_b && (
                  <div className="resumen-diferencia">
                    <div className="resumen-diferencia-general">
                      <span>Ahorro total</span>
                      <span>{fmtPesos(resultado.campana_a.ahorro_total_pesos)}</span>
                      <strong>→</strong>
                      <span>{fmtPesos(resultado.campana_b.ahorro_total_pesos)}</span>
                      <Delta valor={deltaAhorro} formatear={fmtPesos} />
                    </div>
                  </div>
                )}

                <CampanaAhorro
                  titulo={descripcionCultivo(cultivos.find((c) => c.id === resultado.campana_a.cultivo_id))}
                  campana={resultado.campana_a}
                  onCargarPrecio={(productoId, nombre, unidad) => setPrecioForm({ productoId, nombre, unidad })}
                />

                {resultado.campana_b && (
                  <CampanaAhorro
                    titulo={descripcionCultivo(cultivos.find((c) => c.id === resultado.campana_b.cultivo_id))}
                    campana={resultado.campana_b}
                    onCargarPrecio={(productoId, nombre, unidad) => setPrecioForm({ productoId, nombre, unidad })}
                  />
                )}
              </>
            )}
          </>
        )}
      </main>

      {precioForm && (
        <ModalCargarPrecio
          productoId={precioForm.productoId}
          productoNombre={precioForm.nombre}
          unidadSugerida={precioForm.unidad}
          onClose={() => setPrecioForm(null)}
          onGuardado={() => { setPrecioForm(null); calcular() }}
        />
      )}
    </PanelLayout>
  )
}
