import { useState } from 'react'
import client from '../api/client'
import MapaDibujoLote from './MapaDibujoLote'
import MapaNEA from './MapaNEA'
import { TIPOS_SUELO } from '../utils/suelos'
import { AREA_MIN_HA, AREA_MAX_HA } from '../utils/geometria'

export default function ModalNuevoLote({ onSuccess, onClose }) {
  const [form, setForm] = useState({
    nombre: '', tipo_suelo: '',
  })
  const [dibujando, setDibujando] = useState(false)
  const [poligono, setPoligono] = useState(null)
  const [areaM2, setAreaM2] = useState(null)
  const [autointerseccion, setAutointerseccion] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const areaHa = areaM2 != null ? areaM2 / 10000 : null
  const areaFueraDeRango = areaHa != null && (areaHa < AREA_MIN_HA || areaHa > AREA_MAX_HA)

  function onDibujoChange(geojson, areaCalculadaM2, autointerseccionDetectada) {
    setPoligono(geojson)
    setAreaM2(areaCalculadaM2)
    setAutointerseccion(!!autointerseccionDetectada)
    setError('')
  }

  function handleField(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.nombre.trim()) { setError('El nombre del lote es requerido.'); return }
    if (autointerseccion) {
      setError('El polígono tiene lados que se cruzan entre sí — corregilo antes de continuar.')
      return
    }
    if (areaFueraDeRango) {
      setError(`El área del polígono (${areaHa.toFixed(2)} ha) está fuera del rango esperado (${AREA_MIN_HA}-${AREA_MAX_HA} ha).`)
      return
    }

    setLoading(true)
    setError('')
    try {
      const { data } = await client.post('/lotes', {
        nombre: form.nombre.trim(),
        tipo_suelo: form.tipo_suelo || null,
        geometry: poligono,
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
      <div className="modal-box modal-box--wizard" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header modal-header--titulo">
          <h2>Nuevo lote</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <div className="wizard-split">
          <div className="wizard-split-datos">
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
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label htmlFor="tipo_suelo">Tipo de suelo <span className="label-opcional">(opcional)</span></label>
                <select id="tipo_suelo" name="tipo_suelo" value={form.tipo_suelo} onChange={handleField} disabled={loading}>
                  {TIPOS_SUELO.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label>Límites</label>
                <div className="nuevo-lote-limite">
                  <button
                    type="button"
                    className={`modo-limite-btn${dibujando ? ' modo-limite-btn--activo' : ''}`}
                    onClick={() => setDibujando(true)}
                    disabled={loading}
                  >
                    🗺️ Dibujar en mapa
                  </button>
                  <span className="nuevo-lote-o">O al cargar un GeoTIFF se determinarán los límites</span>
                </div>
              </div>

              {areaHa != null && (
                <p className={`area-badge${areaFueraDeRango ? ' area-badge--alerta' : ''}`}>
                  Área del polígono: {areaHa.toFixed(2)} ha
                  {areaFueraDeRango && ' — fuera del rango esperado para un lote agrícola'}
                </p>
              )}
              {autointerseccion && (
                <p className="area-badge area-badge--alerta">
                  ⚠️ El polígono tiene lados que se cruzan entre sí — corregilo antes de guardar.
                </p>
              )}

              {error && <div className="error-message">{error}</div>}

              <div className="modal-actions modal-actions--wizard">
                <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>

          <aside className="wizard-split-mapa">
            {dibujando ? (
              <MapaDibujoLote key="dibujo-nuevo-lote" onChange={onDibujoChange} height="100%" />
            ) : (
              <MapaNEA />
            )}
          </aside>
        </div>
      </div>
    </div>
  )
}
