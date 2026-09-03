import { useState, useEffect } from 'react'
import client from '../api/client'

const PROVINCIAS = [
  { value: 'buenos_aires', label: 'Buenos Aires' },
  { value: 'catamarca', label: 'Catamarca' },
  { value: 'chaco', label: 'Chaco' },
  { value: 'chubut', label: 'Chubut' },
  { value: 'cordoba', label: 'Córdoba' },
  { value: 'corrientes', label: 'Corrientes' },
  { value: 'entre_rios', label: 'Entre Ríos' },
  { value: 'formosa', label: 'Formosa' },
  { value: 'jujuy', label: 'Jujuy' },
  { value: 'la_pampa', label: 'La Pampa' },
  { value: 'la_rioja', label: 'La Rioja' },
  { value: 'mendoza', label: 'Mendoza' },
  { value: 'misiones', label: 'Misiones' },
  { value: 'neuquen', label: 'Neuquén' },
  { value: 'rio_negro', label: 'Río Negro' },
  { value: 'salta', label: 'Salta' },
  { value: 'san_juan', label: 'San Juan' },
  { value: 'san_luis', label: 'San Luis' },
  { value: 'santa_cruz', label: 'Santa Cruz' },
  { value: 'santa_fe', label: 'Santa Fe' },
  { value: 'santiago_del_estero', label: 'Santiago del Estero' },
  { value: 'tierra_del_fuego', label: 'Tierra del Fuego, Antártida e Islas del Atlántico Sur' },
  { value: 'tucuman', label: 'Tucumán' },
  { value: 'caba', label: 'Ciudad Autónoma de Buenos Aires' },
]

export default function ModalNuevoLote({ onSuccess, onClose }) {
  const [form, setForm] = useState({ nombre: '', suelo_id: '', provincia: '', departamento: '', localidad: '' })
  const [suelos, setSuelos] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get('/lotes/suelos').then(({ data }) => {
      setSuelos(data)
      if (data.length > 0) setForm((f) => ({ ...f, suelo_id: f.suelo_id || data[0].id }))
    }).catch(() => setError('No se pudo cargar el catálogo de suelos.'))
  }, [])

  function handleField(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.nombre.trim()) { setError('El nombre del lote es requerido.'); return }
    if (!form.suelo_id) { setError('Seleccioná el tipo de suelo.'); return }
    const algunUbicacion = form.provincia || form.departamento.trim() || form.localidad.trim()
    if (algunUbicacion && !form.provincia) {
      setError('Si cargás la ubicación, seleccioná al menos la provincia.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const { data } = await client.post('/lotes', {
        nombre: form.nombre.trim(),
        suelo_id: form.suelo_id,
        provincia: form.provincia || null,
        departamento: form.departamento.trim() || null,
        localidad: form.localidad.trim() || null,
      })
      onSuccess(data.id)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : detail || 'Error al crear el lote.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--limites" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Nuevo lote</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label htmlFor="nombre">Nombre del lote</label>
            <input
              id="nombre"
              name="nombre"
              type="text"
              placeholder="Ej: Lote Norte — Parcela 3"
              value={form.nombre}
              onChange={handleField}
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="suelo_id">Tipo de suelo</label>
            <select
              id="suelo_id"
              name="suelo_id"
              value={form.suelo_id}
              onChange={handleField}
              disabled={loading || suelos.length === 0}
            >
              {suelos.length === 0 && <option value="">Cargando...</option>}
              {suelos.map((s) => (
                <option key={s.id} value={s.id}>{s.serie ? `${s.tipo} — ${s.serie}` : s.tipo}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="provincia">Provincia <span className="label-opcional">(opcional)</span></label>
            <select
              id="provincia"
              name="provincia"
              value={form.provincia}
              onChange={handleField}
              disabled={loading}
            >
              <option value="">Seleccionar...</option>
              {PROVINCIAS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="departamento">Departamento <span className="label-opcional">(opcional)</span></label>
              <input
                id="departamento"
                name="departamento"
                type="text"
                placeholder="Ej: Presidencia Roque Sáenz Peña"
                maxLength={100}
                value={form.departamento}
                onChange={handleField}
                disabled={loading}
              />
            </div>
            <div className="form-group">
              <label htmlFor="localidad">Localidad <span className="label-opcional">(opcional)</span></label>
              <input
                id="localidad"
                name="localidad"
                type="text"
                maxLength={100}
                value={form.localidad}
                onChange={handleField}
                disabled={loading}
              />
            </div>
          </div>

          <p className="limites-hint">
            El límite geográfico del lote se calcula automáticamente a partir del primer ortomosaico (GeoTIFF) que subas — no hace falta cargarlo acá.
          </p>

          {error && <div className="error-message">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={loading || !form.nombre.trim() || !form.suelo_id}>
              {loading ? 'Creando...' : 'Crear lote'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
