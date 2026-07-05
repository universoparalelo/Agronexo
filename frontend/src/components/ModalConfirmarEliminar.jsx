import { useState } from 'react'

export default function ModalConfirmarEliminar({ titulo, mensaje, onConfirmar, onClose }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleConfirmar() {
    setLoading(true)
    setError('')
    try {
      await onConfirmar()
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : detail || 'Error al eliminar.'
      )
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--confirmar" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{titulo}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <div className="modal-form">
          <p className="confirmar-mensaje">{mensaje}</p>

          {error && <div className="error-message">{error}</div>}

          <div className="modal-actions">
            <button className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button className="btn-danger" onClick={handleConfirmar} disabled={loading}>
              {loading ? 'Eliminando...' : 'Eliminar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
