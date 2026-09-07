const CULTIVO_LABEL = { soja: 'Soja', maiz: 'Maíz', algodon: 'Algodón', sorgo: 'Sorgo' }

export default function ModalElegirLote({ lotes, onElegir, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>¿De qué lote querés ver los análisis?</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <div className="modal-form">
          <div className="elegir-lote-lista">
            {lotes.map((lote) => (
              <button
                key={lote.id}
                type="button"
                className="elegir-lote-item"
                onClick={() => onElegir(lote.id)}
              >
                <span className="elegir-lote-nombre">{lote.nombre}</span>
                <span className="elegir-lote-meta">
                  {CULTIVO_LABEL[lote.cultivo] ?? lote.cultivo}
                  {lote.vuelos ? ` · ${lote.vuelos.length} vuelo${lote.vuelos.length !== 1 ? 's' : ''}` : ''}
                </span>
              </button>
            ))}
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancelar</button>
          </div>
        </div>
      </div>
    </div>
  )
}
