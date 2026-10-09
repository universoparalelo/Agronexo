import useResumenVuelo from '../hooks/useResumenVuelo'

const SEVERIDAD_LABELS = {
  critica: 'Crítica', moderada: 'Moderada', leve: 'Leve', normal: 'Normal', vigorosa: 'Vigorosa',
}
const SEVERIDAD_COLOR = {
  critica: '#ef4444', moderada: '#f59e0b', leve: '#eab308', normal: '#4ade80', vigorosa: '#3b82f6',
}

// El NDVI real puede caer fuera de [0,1] en casos extremos — se clampea solo
// la posición en el gráfico, el número mostrado siempre es el valor real.
function posPct(valor) {
  return `${(Math.max(0, Math.min(1, valor)) * 100).toFixed(1)}%`
}

// Resumen por vuelo en el historial (HU-R4-07): índice con valor medio/mín/
// máx en formato de gráfico, distribución de superficie por severidad, y
// enlaces a prescripción/orden de trabajo/informe PDF cuando corresponde.
// Se monta solo cuando VuelosCalendario expande este vuelo — carga su propio
// diagnóstico de forma independiente del panel principal de resultados.
export default function ResumenVuelo({ loteId, vueloId }) {
  const {
    stats, loading, error,
    descargando, descargaError,
    descargarInforme, descargarOrden, descargarPrescripcion,
  } = useResumenVuelo(loteId, vueloId)

  if (loading) {
    return (
      <div className="resumen-vuelo resumen-vuelo--cargando">
        <span className="diagnostico-spinner" /> Generando resumen...
      </div>
    )
  }

  if (error) return <p className="empty-hint resumen-vuelo-error">{error}</p>
  if (!stats) return null

  return (
    <div className="resumen-vuelo">
      <div className="resumen-vuelo-indice">
        <div className="resumen-vuelo-indice-titulo">
          <span>NDVI</span>
          <span className="resumen-vuelo-indice-recomendado" title={stats.recomendado.motivo}>
            Recomendado para este estadio: {stats.recomendado.indice}
          </span>
        </div>
        <div className="resumen-vuelo-rango-track">
          {stats.ndviMin != null && stats.ndviMax != null && (
            <span
              className="resumen-vuelo-rango-relleno"
              style={{ left: posPct(stats.ndviMin), width: `calc(${posPct(stats.ndviMax)} - ${posPct(stats.ndviMin)})` }}
            />
          )}
          {stats.ndviPromedio != null && (
            <span
              className="resumen-vuelo-rango-marca"
              style={{ left: posPct(stats.ndviPromedio) }}
              title={`Promedio: ${stats.ndviPromedio.toFixed(3)}`}
            />
          )}
        </div>
        <div className="resumen-vuelo-rango-numeros">
          <span>mín {stats.ndviMin != null ? stats.ndviMin.toFixed(3) : '—'}</span>
          <span>prom {stats.ndviPromedio != null ? stats.ndviPromedio.toFixed(3) : '—'}</span>
          <span>máx {stats.ndviMax != null ? stats.ndviMax.toFixed(3) : '—'}</span>
        </div>
      </div>

      <div className="resumen-vuelo-severidad">
        <span className="resumen-vuelo-severidad-titulo">Superficie por severidad</span>
        {stats.severidad.length > 0 ? (
          <>
            <div className="resumen-vuelo-severidad-barra">
              {stats.severidad.map(s => (
                <span
                  key={s.severidad}
                  className="resumen-vuelo-severidad-tramo"
                  style={{ width: `${s.pct}%`, background: SEVERIDAD_COLOR[s.severidad] || '#94a3b8' }}
                  title={`${SEVERIDAD_LABELS[s.severidad] || s.severidad}: ${s.pct.toFixed(1)}%`}
                />
              ))}
            </div>
            <ul className="resumen-vuelo-severidad-leyenda">
              {stats.severidad.map(s => (
                <li key={s.severidad}>
                  <span className="resumen-vuelo-severidad-dot" style={{ background: SEVERIDAD_COLOR[s.severidad] || '#94a3b8' }} />
                  {SEVERIDAD_LABELS[s.severidad] || s.severidad} · {s.pct.toFixed(1)}%
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="empty-hint">Sin zonas clasificadas para este análisis.</p>
        )}
      </div>

      <div className="resumen-vuelo-acciones">
        <button type="button" onClick={descargarInforme} disabled={descargando === 'informe'}>
          {descargando === 'informe' ? 'Generando...' : '📄 Informe PDF'}
        </button>
        <button
          type="button"
          onClick={descargarOrden}
          disabled={descargando === 'orden' || !stats.hayUnidadesManejo}
          title={stats.hayUnidadesManejo ? undefined : 'No hay unidades de manejo para generar una orden de trabajo'}
        >
          {descargando === 'orden' ? 'Generando...' : '📋 Orden de trabajo'}
        </button>
        <button
          type="button"
          onClick={descargarPrescripcion}
          disabled={descargando === 'prescripcion' || !stats.hayZonas}
          title={stats.hayZonas ? undefined : 'Sin zonas clasificadas para exportar'}
        >
          {descargando === 'prescripcion' ? 'Generando...' : '🗂️ Prescripción (SHP)'}
        </button>
      </div>
      {descargaError && <p className="empty-hint resumen-vuelo-error">{descargaError}</p>}
    </div>
  )
}
