import { CAUSAS_REVISABLES } from './RevisionZona'

// Ranking del motor probabilístico (app/diagnostico/bayes.py), en paralelo
// al resultado del motor de reglas. Experimental: las tablas iniciales son
// un borrador experto que se ajusta con las revisiones del agrónomo.
export default function BayesZona({ bayes, causaRegla }) {
  if (!bayes?.ranking?.length) return null
  const top = bayes.ranking[0]
  const coincide = top.causa === causaRegla

  return (
    <div className={`bayes-zona bayes-zona--${bayes.certeza}`}>
      <div className="bayes-zona-header">
        <span className="bayes-zona-titulo">Motor probabilístico <em>(experimental)</em></span>
        <span className="bayes-zona-certeza">{bayes.mensaje}</span>
      </div>
      {bayes.ranking.map((r) => (
        <div key={r.causa} className="bayes-zona-fila">
          <span className="bayes-zona-causa">{CAUSAS_REVISABLES[r.causa] || r.causa}</span>
          <span className="bayes-zona-barra">
            <span style={{ width: `${Math.round(r.probabilidad * 100)}%` }} />
          </span>
          <span className="bayes-zona-pct">{Math.round(r.probabilidad * 100)}%</span>
        </div>
      ))}
      {causaRegla && !coincide && (
        <p className="bayes-zona-nota">No coincide con el motor de reglas — buen candidato para verificar a campo.</p>
      )}
    </div>
  )
}
