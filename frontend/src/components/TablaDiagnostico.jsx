const CONFIANZA_LABELS = {
  alta:  'Confianza alta',
  media: 'Confianza media — confirmar en campo',
  baja:  'Confianza baja — orientativo',
}

const SEVERIDAD_COLORS = {
  critica:  'severidad-critica',
  moderada: 'severidad-moderada',
  leve:     'severidad-leve',
  normal:   'severidad-normal',
  vigorosa: 'severidad-vigorosa',
}

const SEVERIDAD_LABELS = {
  critica:  'Crítica',
  moderada: 'Moderada',
  leve:     'Leve',
  normal:   'Normal',
  vigorosa: 'Vigorosa',
}

export default function TablaDiagnostico({ diagnostico }) {
  const features = diagnostico?.features || []
  const metadata = diagnostico?.metadata

  if (features.length === 0) {
    return <p className="empty-hint">Sin zonas para diagnosticar.</p>
  }

  const ordenadas = [...features].sort((a, b) => {
    const aOk = a.properties?.regla_id === 'R99' ? 1 : 0
    const bOk = b.properties?.regla_id === 'R99' ? 1 : 0
    return aOk - bOk
  })

  return (
    <div className="tabla-diagnostico-wrapper">
      <h3 className="tabla-zonas-title">Diagnóstico agronómico</h3>

      {metadata && (
        <div className="diagnostico-header-info">
          <p className="diagnostico-metadata">
            {metadata.lote_nombre && <strong>{metadata.lote_nombre}</strong>}
            {metadata.lote_nombre && ' · '}
            {metadata.cultivo} · estadio {metadata.estadio_fenologico || 'sin cargar'}
            {metadata.fecha_vuelo && ` · vuelo del ${new Date(metadata.fecha_vuelo).toLocaleDateString('es-AR')}`}
            {' · '}índices usados: {metadata.indices_disponibles?.join(', ') || 'ndvi'}
          </p>
          {metadata.resumen_general && (
            <p className="diagnostico-resumen">{metadata.resumen_general}</p>
          )}
        </div>
      )}

      <div className="diagnostico-lista">
        {ordenadas.map((f, i) => {
          const p = f.properties || {}
          const sinProblema = p.regla_id === 'R99'
          const severidad = p.severidad || 'normal'
          return (
            <div key={i} className={`diagnostico-card confianza-${p.confianza || 'media'} ${sinProblema ? 'diagnostico-card--ok' : ''}`}>
              <div className="diagnostico-card-header">
                <span className="diagnostico-regla-nombre">{p.regla_nombre || 'Sin diagnóstico'}</span>
                <div className="diagnostico-badges">
                  {!sinProblema && (
                    <span className={`diagnostico-badge ${SEVERIDAD_COLORS[severidad] || 'severidad-normal'}`}>
                      {SEVERIDAD_LABELS[severidad] || severidad}
                    </span>
                  )}
                  <span className={`diagnostico-badge confianza-badge-${p.confianza || 'media'}`}>
                    {CONFIANZA_LABELS[p.confianza] || p.confianza}
                  </span>
                </div>
              </div>

              <div className="diagnostico-card-meta">
                <span>{p.area_ha?.toFixed(2) ?? '—'} ha</span>
                <span>·</span>
                <span>patrón: {p.patron_espacial || '—'}</span>
                <span>·</span>
                <span>NDVI: {p.ndvi_promedio?.toFixed(3) ?? '—'}</span>
              </div>

              {p.texto_explicativo && (
                <p className="diagnostico-texto-explicativo">{p.texto_explicativo}</p>
              )}

              {!sinProblema && (
                <>
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

      {diagnostico?.unidades_manejo?.length > 0 && (
        <div className="unidades-manejo-section">
          <h3 className="tabla-zonas-title">Unidades de manejo</h3>
          <p className="unidades-manejo-desc">
            Zonas agrupadas por causa y severidad para prescripción diferenciada.
          </p>
          <div className="unidades-manejo-lista">
            {diagnostico.unidades_manejo.map((u) => {
              const p = u.properties || {}
              return (
                <div key={p.unidad_id} className={`unidad-card ${SEVERIDAD_COLORS[p.severidad] || ''}`}>
                  <div className="unidad-card-header">
                    <span className="unidad-card-titulo">Unidad #{p.unidad_id}</span>
                    <span className={`diagnostico-badge ${SEVERIDAD_COLORS[p.severidad] || 'severidad-normal'}`}>
                      {SEVERIDAD_LABELS[p.severidad] || p.severidad}
                    </span>
                  </div>
                  <div className="unidad-card-meta">
                    <span>{p.area_total_ha} ha</span>
                    <span>·</span>
                    <span>{p.n_zonas} zona{p.n_zonas !== 1 ? 's' : ''}</span>
                    {p.ndvi_promedio != null && (
                      <>
                        <span>·</span>
                        <span>NDVI: {p.ndvi_promedio.toFixed(3)}</span>
                      </>
                    )}
                  </div>
                  <p className="unidad-card-causa">{p.regla_nombre}</p>
                  {p.texto_unidad && (
                    <p className="unidad-card-texto">{p.texto_unidad}</p>
                  )}
                  {p.productos_sugeridos?.length > 0 && (
                    <div className="diagnostico-productos">
                      {p.productos_sugeridos.map((prod, j) => (
                        <span key={j} className="producto-chip">{prod.nombre}</span>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
