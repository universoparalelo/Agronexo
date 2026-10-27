import { useState } from 'react'
import { etiquetasUnicas } from '../utils/vuelos'

// vuelos: solo los completados del lote. Se comparan siempre de más viejo a más nuevo.
export default function ModalCompararVuelos({ vuelos, onComparar, onClose }) {
  const porFecha = [...vuelos].sort((a, b) => new Date(b.fecha_vuelo) - new Date(a.fecha_vuelo))
  const etiquetas = etiquetasUnicas(porFecha)
  const [anteriorId, setAnteriorId] = useState(porFecha[1]?.vuelo_id ?? '')
  const [posteriorId, setPosteriorId] = useState(porFecha[0]?.vuelo_id ?? '')

  const mismoVuelo = anteriorId === posteriorId

  function confirmar(e) {
    e.preventDefault()
    if (mismoVuelo) return
    const a = vuelos.find(v => v.vuelo_id === anteriorId)
    const b = vuelos.find(v => v.vuelo_id === posteriorId)
    const [base, otro] = new Date(a.fecha_vuelo) <= new Date(b.fecha_vuelo) ? [a, b] : [b, a]
    onComparar(base.vuelo_id, otro.vuelo_id)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Comparar vuelos</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <form className="modal-form" onSubmit={confirmar}>
          <div className="form-group">
            <label htmlFor="comparar-anterior">Vuelo anterior</label>
            <select id="comparar-anterior" value={anteriorId} onChange={(e) => setAnteriorId(e.target.value)}>
              {porFecha.map((v, i) => <option key={v.vuelo_id} value={v.vuelo_id}>{etiquetas[i]}</option>)}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="comparar-posterior">Vuelo posterior</label>
            <select id="comparar-posterior" value={posteriorId} onChange={(e) => setPosteriorId(e.target.value)}>
              {porFecha.map((v, i) => <option key={v.vuelo_id} value={v.vuelo_id}>{etiquetas[i]}</option>)}
            </select>
          </div>

          {mismoVuelo && <p className="error-message">Elegí dos vuelos distintos.</p>}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={mismoVuelo}>Comparar</button>
          </div>
        </form>
      </div>
    </div>
  )
}
