import { useEffect } from 'react'

export default function ModalMapaAmpliado({ titulo = 'Mapa del lote', onClose, children }) {
  useEffect(() => {
    function alTeclear(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', alTeclear)
    return () => window.removeEventListener('keydown', alTeclear)
  }, [onClose])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--mapa" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{titulo}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>
        <div className="mapa-ampliado-cuerpo">{children}</div>
      </div>
    </div>
  )
}
