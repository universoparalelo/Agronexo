import { useState } from 'react'
import { cargarPrecioProducto } from '../api/ahorro'

// Form chico para cargar el precio real pagado de un producto (HU-R4-11) —
// se abre desde la pantalla de Ahorro comparativo cuando un producto usado
// en la orden de trabajo todavía no tiene precio cargado. No hay pantalla
// de catálogo/admin de productos en el proyecto, así que este es el único
// punto de entrada para cargar precios.
export default function ModalCargarPrecio({ productoId, productoNombre, unidadSugerida, onClose, onGuardado }) {
  const [precioUsd, setPrecioUsd] = useState('')
  const [unidad, setUnidad] = useState(unidadSugerida || '')
  const [fecha, setFecha] = useState(() => new Date().toISOString().slice(0, 10))
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setGuardando(true)
    setError('')
    try {
      await cargarPrecioProducto(productoId, {
        precio_usd: parseFloat(precioUsd),
        unidad,
        fecha,
      })
      onGuardado()
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : detail || 'No se pudo cargar el precio.'
      )
      setGuardando(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Cargar precio — {productoNombre}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="precio_usd">Precio (USD)</label>
              <input
                id="precio_usd"
                type="number"
                step="0.01"
                min="0.01"
                required
                value={precioUsd}
                onChange={(e) => setPrecioUsd(e.target.value)}
                disabled={guardando}
              />
            </div>
            <div className="form-group">
              <label htmlFor="unidad">Unidad</label>
              <input
                id="unidad"
                type="text"
                placeholder="L, kg..."
                required
                value={unidad}
                onChange={(e) => setUnidad(e.target.value)}
                disabled={guardando}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="fecha">Fecha de compra</label>
            <input
              id="fecha"
              type="date"
              required
              max={new Date().toISOString().slice(0, 10)}
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              disabled={guardando}
            />
          </div>

          {error && <p className="error-message">{error}</p>}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={guardando}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={guardando}>
              {guardando ? 'Guardando...' : 'Guardar precio'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
