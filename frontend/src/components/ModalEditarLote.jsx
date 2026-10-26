import { useState } from 'react'
import { actualizarLote } from '../api/lotes'
import { TIPOS_SUELO } from '../utils/suelos'

export default function ModalEditarLote({ lote, onSuccess, onClose }) {
  const [form, setForm] = useState({
    nombre: lote.nombre || '',
    tipo_suelo: lote.tipo_suelo || '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function handleField(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.nombre.trim()) { setError('El nombre del lote es requerido.'); return }

    setLoading(true)
    setError('')
    try {
      // El PUT ignora los campos en null, así que "Seleccionar..." deja el tipo de suelo como estaba.
      await actualizarLote(lote.id, {
        nombre: form.nombre.trim(),
        tipo_suelo: form.tipo_suelo || null,
      })
      onSuccess()
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : detail || 'Error al guardar el lote.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header modal-header--titulo">
          <h2>Editar lote</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label htmlFor="editar-nombre">Nombre del lote</label>
            <input
              id="editar-nombre"
              name="nombre"
              type="text"
              value={form.nombre}
              onChange={handleField}
              disabled={loading}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="editar-tipo-suelo">Tipo de suelo <span className="label-opcional">(opcional)</span></label>
            <select id="editar-tipo-suelo" name="tipo_suelo" value={form.tipo_suelo} onChange={handleField} disabled={loading}>
              {TIPOS_SUELO.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
