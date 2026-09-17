import { useEffect, useState } from 'react'
import { descargarBlob } from '../utils/descargarArchivo'

// El blob ya viene descargado (fetch con responseType:'blob') — acá solo lo
// mostramos con el visor de PDF nativo del navegador vía un blob: URL, sin
// pegarle de nuevo al backend. El botón "Descargar" reusa el mismo blob en
// vez de pedirlo otra vez (evita regenerar el PDF dos veces con WeasyPrint).
export default function ModalPreviewPdf({ titulo, blob, filename, onClose }) {
  const [url, setUrl] = useState(null)

  useEffect(() => {
    const objectUrl = URL.createObjectURL(blob)
    setUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [blob])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--preview-pdf" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{titulo}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <div className="preview-pdf-body">
          {url && <iframe src={url} title={titulo} className="preview-pdf-iframe" />}
        </div>

        <div className="preview-pdf-footer">
          <button className="btn-secondary" onClick={onClose}>Cerrar</button>
          <button className="btn-primary" onClick={() => descargarBlob(blob, filename)}>
            Descargar PDF
          </button>
        </div>
      </div>
    </div>
  )
}
