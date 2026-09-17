import { useState } from 'react'

const CONFIANZA_LABELS = {
  alta:  'Confianza alta',
  media: 'Confianza media — confirmar en campo',
  baja:  'Confianza baja — orientativo',
}

const CONFIANZA_CORTO = {
  alta:  'Alta',
  media: 'Media',
  baja:  'Baja',
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

const CAUSA_LABELS = {
  sin_problema_detectado: 'Sin problema',
  interferencia_vegetacion: 'Malezas',
  estres_biotico_fungico: 'Hongo',
  estres_biotico_insecto: 'Insecto',
  estres_nutricional_nitrogeno: 'Déficit N',
  estres_nutricional_micro: 'Déficit micro',
  estres_nutricional_fosforo: 'Déficit P',
  estres_hidrico: 'Estrés hídrico',
  madurez_temprana_diferencial: 'Madurez dif.',
  vigor_excesivo: 'Vigor excesivo',
}

export default function TablaDiagnostico({
  diagnostico, onRecalcular, recalculando, onGenerarOrdenTrabajo, generandoOrden,
}) {
  const features = diagnostico?.features || []
  const metadata = diagnostico?.metadata
  const [vista, setVista] = useState('tabla')

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
      <div className="diagnostico-title-row">
        <h3 className="tabla-zonas-title">Diagnóstico agronómico</h3>
        <div className="diagnostico-title-row-controles">
          <button
            type="button"
            className="btn-recalcular-diagnostico"
            onClick={onRecalcular}
            disabled={recalculando}
            title="Vuelve a calcular el diagnóstico desde cero y reemplaza el guardado"
          >
            {recalculando ? 'Recalculando...' : '↻ Recalcular'}
          </button>
          {diagnostico?.unidades_manejo?.length > 0 && (
            <button
              type="button"
              className="btn-recalcular-diagnostico"
              onClick={onGenerarOrdenTrabajo}
              disabled={generandoOrden}
              title="Genera el PDF de orden de trabajo con las dosis por unidad de manejo"
            >
              {generandoOrden ? 'Generando orden...' : '📋 Generar orden de trabajo'}
            </button>
          )}
          <div className="diagnostico-vista-toggle">
            <button
              className={`vista-btn ${vista === 'tabla' ? 'vista-btn--active' : ''}`}
              onClick={() => setVista('tabla')}
              title="Vista tabla"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="1" width="12" height="3" rx="0.5" fill="currentColor"/><rect x="1" y="5.5" width="12" height="3" rx="0.5" fill="currentColor" opacity="0.6"/><rect x="1" y="10" width="12" height="3" rx="0.5" fill="currentColor" opacity="0.35"/></svg>
            </button>
            <button
              className={`vista-btn ${vista === 'cards' ? 'vista-btn--active' : ''}`}
              onClick={() => setVista('cards')}
              title="Vista detalle"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="1" width="5.5" height="5.5" rx="1" fill="currentColor"/><rect x="7.5" y="1" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.6"/><rect x="1" y="7.5" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.6"/><rect x="7.5" y="7.5" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.35"/></svg>
            </button>
          </div>
        </div>
      </div>

      {metadata && (
        <div className="diagnostico-header-info">
          <p className="diagnostico-metadata">
            {metadata.lote_nombre && <strong>{metadata.lote_nombre}</strong>}
            {metadata.lote_nombre && ' · '}
            {metadata.cultivo} · estadio {metadata.estadio_fenologico || 'sin cargar'}
            {metadata.fecha_vuelo && ` · vuelo del ${new Date(metadata.fecha_vuelo).toLocaleDateString('es-AR')}`}
            {' · '}índices usados: {metadata.indices_disponibles?.join(', ') || 'ndvi'}
            {metadata.calculado_en && (
              <span className="diagnostico-calculado-en">
                {' · '}calculado el {new Date(metadata.calculado_en).toLocaleString('es-AR', {
                  day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
                })}
              </span>
            )}
          </p>
          {metadata.resumen_general && (
            <p className="diagnostico-resumen">{metadata.resumen_general}</p>
          )}
        </div>
      )}

      {vista === 'tabla' && (
        <div className="stats-table-wrap">
          <table className="stats-table">
            <thead>
              <tr>
                <th>Zona</th>
                <th>Área</th>
                <th>NDVI</th>
                <th>Severidad</th>
                <th>Causa</th>
                <th>Conf.</th>
                <th>Producto</th>
              </tr>
            </thead>
            <tbody>
              {ordenadas.map((f, i) => {
                const p = f.properties || {}
                const sinProblema = p.regla_id === 'R99'
                const severidad = p.severidad || 'normal'
                const producto = p.productos_sugeridos?.[0]?.nombre || '—'
                return (
                  <tr key={i} className={sinProblema ? 'stats-row--ok' : ''}>
                    <td className="stats-zona-id">Z{p.zona_id ?? i}</td>
                    <td>{p.area_ha?.toFixed(2) ?? '—'}</td>
                    <td className="stats-ndvi">{p.ndvi_promedio?.toFixed(3) ?? '—'}</td>
                    <td>
                      <span className={`stats-badge ${SEVERIDAD_COLORS[severidad] || ''}`}>
                        {SEVERIDAD_LABELS[severidad] || severidad}
                      </span>
                    </td>
                    <td className="stats-causa">{CAUSA_LABELS[p.causa_indice] || p.causa_indice || '—'}</td>
                    <td>
                      <span className={`stats-badge confianza-badge-${p.confianza || 'media'}`}>
                        {CONFIANZA_CORTO[p.confianza] || p.confianza || '—'}
                      </span>
                    </td>
                    <td className="stats-producto">{sinProblema ? '—' : producto}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {vista === 'cards' && (
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
      )}

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
