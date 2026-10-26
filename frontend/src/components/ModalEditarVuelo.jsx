import { useEffect, useState } from 'react'
import { actualizarVuelo, listarEstadiosFenologicos } from '../api/analisis'
import { etiquetaTipoCultivo } from '../utils/cultivos'
import { fechaISOLocal } from '../utils/fechas'

export default function ModalEditarVuelo({ loteId, vuelo, cultivos, onSuccess, onClose }) {
  const [form, setForm] = useState({
    fecha: fechaISOLocal(new Date(vuelo.fecha_vuelo)),
    estadio: vuelo.estadio_fenologico || '',
    cultivoId: vuelo.cultivo_id || '',
  })
  const [estadiosPorCultivo, setEstadiosPorCultivo] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    listarEstadiosFenologicos().then(setEstadiosPorCultivo).catch(() => {})
  }, [])

  const tipoCultivo = cultivos.find((c) => c.id === form.cultivoId)?.tipo_cultivo
  const estadios = estadiosPorCultivo[tipoCultivo] ?? []
  // Un estadio guardado puede no estar en la lista del cultivo (datos viejos): se mantiene como opción.
  const opcionesEstadio = form.estadio && !estadios.includes(form.estadio) ? [form.estadio, ...estadios] : estadios

  function handleField(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.fecha) { setError('La fecha del vuelo es requerida.'); return }
    if (!form.estadio.trim()) { setError('El estadio fenológico es requerido.'); return }

    setLoading(true)
    setError('')
    try {
      const datos = {
        // Mediodía local para que la zona horaria no corra el día al guardar.
        fecha_vuelo: new Date(`${form.fecha}T12:00:00`).toISOString(),
        estadio_fenologico: form.estadio.trim(),
      }
      if (form.cultivoId) datos.cultivo_id = form.cultivoId
      const resultado = await actualizarVuelo(loteId, vuelo.vuelo_id, datos)
      if (resultado.diagnostico_desactualizado) {
        setAviso('Como cambió el cultivo o el estadio, el diagnóstico ya calculado quedó desactualizado: abrilo y apretá "Recalcular".')
        setLoading(false)
        return
      }
      onSuccess()
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : detail || 'Error al guardar el vuelo.'
      )
      setLoading(false)
    }
  }

  if (aviso) {
    return (
      <div className="modal-overlay" onClick={onSuccess}>
        <div className="modal-box" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header modal-header--titulo">
            <h2>Vuelo actualizado</h2>
          </div>
          <p>{aviso}</p>
          <div className="modal-actions">
            <button type="button" className="btn-primary" onClick={onSuccess}>Entendido</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header modal-header--titulo">
          <h2>Editar vuelo</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label htmlFor="editar-vuelo-fecha">Fecha del vuelo</label>
            <input id="editar-vuelo-fecha" name="fecha" type="date" value={form.fecha} onChange={handleField} disabled={loading} />
          </div>

          <div className="form-group">
            <label htmlFor="editar-vuelo-cultivo">Cultivo</label>
            <select id="editar-vuelo-cultivo" name="cultivoId" value={form.cultivoId} onChange={handleField} disabled={loading}>
              {!form.cultivoId && <option value="">Sin cultivo</option>}
              {cultivos.map((c) => (
                <option key={c.id} value={c.id}>
                  {etiquetaTipoCultivo(c.tipo_cultivo)}{c.variedad ? ` — ${c.variedad}` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="editar-vuelo-estadio">Estadio fenológico</label>
            <select id="editar-vuelo-estadio" name="estadio" value={form.estadio} onChange={handleField} disabled={loading}>
              {opcionesEstadio.map((e) => <option key={e} value={e}>{e}</option>)}
            </select>
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
