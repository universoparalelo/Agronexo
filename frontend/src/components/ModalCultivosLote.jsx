import { useEffect, useState } from 'react'
import { listarCultivosLote } from '../api/lotes'

const CULTIVO_LABEL = { soja: 'Soja', maiz: 'Maíz', algodon: 'Algodón', sorgo: 'Sorgo' }

function fmtFecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function ModalCultivosLote({ lote, onClose }) {
  const [cultivos, setCultivos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    listarCultivosLote(lote.id)
      .then(setCultivos)
      .catch(() => setError('No se pudo cargar el historial de cultivos.'))
      .finally(() => setLoading(false))
  }, [lote.id])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--cultivos" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Cultivos — {lote.nombre}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <div className="modal-form">
          {loading ? (
            <p className="estado-msg">Cargando cultivos...</p>
          ) : error ? (
            <div className="error-message">{error}</div>
          ) : cultivos.length === 0 ? (
            <div className="empty-state">
              <p>Este lote todavía no tiene ciclos de cultivo registrados.</p>
              <p className="empty-hint">Se registran automáticamente al cargar un vuelo.</p>
            </div>
          ) : (
            <ul className="cultivos-lista">
              {cultivos.map((c) => (
                <li key={c.id} className="cultivos-item">
                  <div className="cultivos-item-top">
                    <span className={`cultivo-badge cultivo-${c.cultivo}`}>
                      {CULTIVO_LABEL[c.cultivo] ?? c.cultivo}
                    </span>
                    {c.activo && <span className="estado-badge estado-completado">Activo</span>}
                    {c.estadio_fenologico && (
                      <span className="cultivos-estadio">{c.estadio_fenologico}</span>
                    )}
                  </div>
                  <div className="cultivos-item-fechas">
                    <span>Siembra: {fmtFecha(c.fecha_siembra)}</span>
                    <span>Cosecha estimada: {fmtFecha(c.fecha_cosecha_estimada)}</span>
                    <span>Cosecha real: {fmtFecha(c.fecha_cosecha_real)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div className="modal-actions">
            <button className="btn-secondary" onClick={onClose}>Cerrar</button>
          </div>
        </div>
      </div>
    </div>
  )
}
