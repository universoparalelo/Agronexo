const CONFIANZA_LABELS = {
  alta:  'Confianza alta',
  media: 'Confianza media — confirmar en campo',
  baja:  'Confianza baja — orientativo',
}

export default function TablaDiagnostico({ diagnostico }) {
  const features = diagnostico?.features || []
  const metadata = diagnostico?.metadata

  if (features.length === 0) {
    return <p className="empty-hint">Sin zonas para diagnosticar.</p>
  }

  // Zonas sin problema (R99) van al final, no aportan nada accionable arriba.
  const ordenadas = [...features].sort((a, b) => {
    const aOk = a.properties?.regla_id === 'R99' ? 1 : 0
    const bOk = b.properties?.regla_id === 'R99' ? 1 : 0
    return aOk - bOk
  })

  return (
    <div className="tabla-diagnostico-wrapper">
      <h3 className="tabla-zonas-title">Diagnóstico agronómico</h3>

      {metadata && (
        <p className="diagnostico-metadata">
          {metadata.cultivo} · estadio {metadata.estadio_fenologico || 'sin cargar'} ·
          {' '}índices usados: {metadata.indices_disponibles?.join(', ') || 'ndvi'}
        </p>
      )}

      <div className="diagnostico-lista">
        {ordenadas.map((f, i) => {
          const p = f.properties || {}
          const sinProblema = p.regla_id === 'R99'
          return (
            <div key={i} className={`diagnostico-card confianza-${p.confianza || 'media'} ${sinProblema ? 'diagnostico-card--ok' : ''}`}>
              <div className="diagnostico-card-header">
                <span className="diagnostico-regla-nombre">{p.regla_nombre || 'Sin diagnóstico'}</span>
                <span className={`diagnostico-badge confianza-badge-${p.confianza || 'media'}`}>
                  {CONFIANZA_LABELS[p.confianza] || p.confianza}
                </span>
              </div>

              <div className="diagnostico-card-meta">
                <span>{p.area_ha?.toFixed(2) ?? '—'} ha</span>
                <span>·</span>
                <span>patrón: {p.patron_espacial || '—'}</span>
                <span>·</span>
                <span>NDVI: {p.ndvi_promedio?.toFixed(3) ?? '—'}</span>
              </div>

              {!sinProblema && (
                <>
                  <p className="diagnostico-accion">
                    <strong>Acción recomendada:</strong> {p.accion_recomendada}
                  </p>
                  <details className="diagnostico-confirmar">
                    <summary>Cómo confirmar en campo</summary>
                    <p>{p.como_confirmar_campo}</p>
                  </details>
                  {p.productos_sugeridos?.length > 0 && (
                    <div className="diagnostico-productos">
                      {p.productos_sugeridos.map((prod, j) => (
                        <span key={j} className="producto-chip">{prod.nombre}</span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
