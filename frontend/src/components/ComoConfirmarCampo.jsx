// Guía de verificación a campo pensada para alguien sin experiencia: los
// textos de cada regla dicen QUÉ buscar; acá se agregan el antes (llegar a
// la zona) y el después (comparar y dejar el criterio técnico cargado).
// En un diagnóstico diferencial (R80) el texto trae un bloque por causa
// separado por una línea en blanco: cada bloque es un paso.
export default function ComoConfirmarCampo({ zona }) {
  const texto = zona.como_confirmar_campo
  if (!texto) return null

  const sinProblema = zona.regla_id === 'R99'
  if (sinProblema) {
    return (
      <div className="como-confirmar como-confirmar--ok">
        <span className="como-confirmar-titulo">Cómo verificar en campo</span>
        <p>{texto}</p>
      </div>
    )
  }

  const pasos = [
    `Ubicá la zona Z${zona.zona_id} en el mapa (${zona.area_ha?.toFixed(1) ?? '—'} ha) y caminá hasta ella. Si es grande, recorré al menos 3 puntos distintos.`,
    ...texto.split(/\n\s*\n/).map(t => t.trim()).filter(Boolean),
    'Compará lo que ves con plantas de una zona sana del mismo lote: altura, color de las hojas y cantidad de plantas.',
    'Volvé acá y cargá el resultado abajo, en "Criterio técnico": Aceptar si se confirmó, Modificar si encontraste otra causa, Rechazar si no hay problema.',
  ]

  return (
    <div className="como-confirmar">
      <span className="como-confirmar-titulo">Cómo confirmar en campo — paso a paso</span>
      <ol>
        {pasos.map((paso, i) => <li key={i}>{paso}</li>)}
      </ol>
    </div>
  )
}
