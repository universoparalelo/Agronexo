import { useEffect, useState } from 'react'
import BayesZona from './BayesZona'
import ComoConfirmarCampo from './ComoConfirmarCampo'
import RevisionZona from './RevisionZona'

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

const REVISION_ICONO = { aceptado: '✓', modificado: '✎', rechazado: '✕' }

// Causa de la regla en las clases del motor probabilístico — espejo de
// app/diagnostico/bayes.py::causa_efectiva.
function causaEfectiva(p) {
  if (p.regla_id === 'R01') return 'suelo_desnudo'
  if (p.causa_indice === 'bajo_vigor_estadio') return null
  return p.causa_indice
}

function revisionesIniciales(features) {
  return Object.fromEntries(
    features.map(f => [f.properties?.zona_id, f.properties?.revision ?? null]),
  )
}

const CONFIABILIDAD_DOSIS = {
  marbete: 'según marbete',
  web: 'habitual según web',
}

const formatoUsd = (n) => (n == null ? '—' : `USD ${n.toFixed(2)}`)

const sinTildes = (t) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

// La variante del catálogo suele repetir marca y concentración ("250 SC — genérico"):
// se muestra solo si agrega algo, como "uso herbicida" en Paraquat.
function detalleMarca(m) {
  const partes = [m.concentracion]
  const variante = m.variante
  if (variante) {
    const v = sinTildes(variante)
    const repite = v.includes(sinTildes(m.marca)) || (m.concentracion && v.includes(sinTildes(m.concentracion)))
    if (!repite) partes.push(variante)
  }
  return partes.filter(Boolean).join(' · ')
}

function ProductosSugeridos({ productos, alternativas }) {
  if (!productos?.length) return null
  return (
    <div className="diagnostico-productos">
      {productos.map((prod, j) => {
        const marcas = alternativas?.[prod.nombre] || []
        if (marcas.length === 0) {
          return <span key={j} className="producto-chip">{prod.nombre}</span>
        }
        return (
          <details key={j} className="producto-alternativas">
            <summary className="producto-chip">
              {prod.nombre} · {marcas.length} {marcas.length === 1 ? 'marca' : 'marcas'}
            </summary>
            <table className="producto-alternativas-tabla">
              <thead>
                <tr><th>Marca</th><th>Dosis</th><th>Precio</th><th>Costo/ha</th></tr>
              </thead>
              <tbody>
                {marcas.map((m, k) => (
                  <tr key={k}>
                    <td>
                      {m.marca}
                      {detalleMarca(m) && <small>{detalleMarca(m)}</small>}
                    </td>
                    <td>
                      {m.dosis_por_ha} {m.unidad_dosis}
                      {m.confiabilidad_dosis && <small> {CONFIABILIDAD_DOSIS[m.confiabilidad_dosis] || m.confiabilidad_dosis}</small>}
                    </td>
                    <td>{formatoUsd(m.precio_usd)}/{m.unidad_precio}</td>
                    <td>{formatoUsd(m.costo_por_ha_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="producto-alternativas-aviso">
              Ordenadas de menor a mayor costo por hectárea. Verificá en el marbete que sea apto para tu cultivo.
            </p>
          </details>
        )
      })}
    </div>
  )
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
  compactacion_falla_siembra: 'Compactación / siembra',
  bajo_vigor_estadio: 'Vigor bajo p/ estadio',
}

export default function TablaDiagnostico({
  diagnostico,
}) {
  const features = diagnostico?.features || []
  const metadata = diagnostico?.metadata
  // Detalle por defecto: es la única vista con la guía de campo, el motor
  // probabilístico y el criterio técnico — la tabla es un resumen.
  const [vista, setVista] = useState('cards')
  const [zonaDestacada, setZonaDestacada] = useState(null)

  function irAZona(zonaId) {
    setVista('cards')
    setZonaDestacada(zonaId)
    requestAnimationFrame(() => {
      document.getElementById(`diag-zona-${zonaId}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }
  const [revisiones, setRevisiones] = useState(() => revisionesIniciales(features))

  // Recalcular trae un diagnóstico nuevo (con sus revisiones adjuntas).
  useEffect(() => { setRevisiones(revisionesIniciales(diagnostico?.features || [])) }, [diagnostico])

  const actualizarRevision = (zonaId, revision) => setRevisiones(r => ({ ...r, [zonaId]: revision }))
  const nRevisadas = Object.values(revisiones).filter(Boolean).length

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
        <div className="seccion-encabezado">
          <h3 className="tabla-zonas-title">Diagnóstico por zona</h3>
          {metadata?.calculado_en && (
            <p className="seccion-sub">
              Calculado el {new Date(metadata.calculado_en).toLocaleString('es-AR', {
                day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
              })}
            </p>
          )}
        </div>
        <div className="diagnostico-title-row-controles">
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

      <p className="diagnostico-revisadas">
        {nRevisadas} de {features.length} zonas con criterio técnico cargado
        {vista === 'tabla' ? ' — tocá una zona para ver cómo confirmarla en campo y validarla.' : '.'}
      </p>

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
                <th title="Criterio técnico del agrónomo">Rev.</th>
              </tr>
            </thead>
            <tbody>
              {ordenadas.map((f, i) => {
                const p = f.properties || {}
                const sinProblema = p.regla_id === 'R99'
                const severidad = p.severidad || 'normal'
                const producto = p.productos_sugeridos?.[0]?.nombre || '—'
                return (
                  <tr
                    key={i}
                    className={`stats-row--clickable ${sinProblema ? 'stats-row--ok' : ''}`}
                    onClick={() => irAZona(p.zona_id)}
                    title="Ver detalle, cómo confirmar en campo y validar esta zona"
                  >
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
                    <td>
                      {revisiones[p.zona_id]
                        ? (
                          <span
                            className={`revision-badge revision-badge--${revisiones[p.zona_id].decision}`}
                            title={revisiones[p.zona_id].decision}
                          >
                            {REVISION_ICONO[revisiones[p.zona_id].decision]}
                          </span>
                        )
                        : <span className="td-vacio">—</span>}
                    </td>
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
              <div
                key={i}
                id={`diag-zona-${p.zona_id}`}
                className={`diagnostico-card confianza-${p.confianza || 'media'} ${sinProblema ? 'diagnostico-card--ok' : ''} ${zonaDestacada === p.zona_id ? 'diagnostico-card--destacada' : ''}`}
              >
                <div className="diagnostico-card-header">
                  <span className="diagnostico-regla-nombre">Z{p.zona_id} · {p.regla_nombre || 'Sin diagnóstico'}</span>
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
                    {p.accion_recomendada && (
                      <p className="diagnostico-accion">
                        <strong>Acción recomendada:</strong> {p.accion_recomendada}
                      </p>
                    )}
                    <ProductosSugeridos productos={p.productos_sugeridos} alternativas={diagnostico?.alternativas_marca} />
                  </>
                )}

                {!p.excluida && <ComoConfirmarCampo zona={p} />}

                {!p.excluida && <BayesZona bayes={p.bayes} causaRegla={causaEfectiva(p)} />}

                {!p.excluida && metadata?.lote_id && metadata?.vuelo_id && (
                  <RevisionZona
                    loteId={metadata.lote_id}
                    vueloId={metadata.vuelo_id}
                    zonaId={p.zona_id}
                    causaSugerida={causaEfectiva(p)}
                    revision={revisiones[p.zona_id]}
                    bayes={p.bayes}
                    onCambio={actualizarRevision}
                  />
                )}
              </div>
            )
          })}
        </div>
      )}

      {diagnostico?.unidades_manejo?.length > 0 && (
        <div className="unidades-manejo-section">
          <div className="seccion-encabezado">
            <h3 className="tabla-zonas-title titulo-con-ayuda">
              Unidades de manejo
              <span className="ayuda-tip">
                <button type="button" className="ayuda-tip-boton" aria-label="¿Qué son las unidades de manejo?">i</button>
                <span role="tooltip" className="ayuda-tip-caja">
                  Zonas agrupadas por causa y severidad para prescripción diferenciada.
                </span>
              </span>
            </h3>
          </div>
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
                  <div className="unidad-card-cuerpo">
                    <div>
                      <p className="unidad-card-causa">{p.regla_nombre}</p>
                      <div className="unidad-card-meta">
                        <span>{p.n_zonas} zona{p.n_zonas !== 1 ? 's' : ''}</span>
                        {p.ndvi_promedio != null && (
                          <>
                            <span>·</span>
                            <span>NDVI {p.ndvi_promedio.toFixed(3)}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <span className="unidad-card-area">{Number(p.area_total_ha).toFixed(1).replace('.', ',')} ha</span>
                  </div>
                  {p.accion_recomendada && (
                    <p className="unidad-card-texto">{p.accion_recomendada.split('. ')[0].replace(/\.$/, '')}.</p>
                  )}
                  <ProductosSugeridos productos={p.productos_sugeridos} alternativas={diagnostico?.alternativas_marca} />
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
