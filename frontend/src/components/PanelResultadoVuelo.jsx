import { useState } from 'react'
import useResultadoVuelo from '../hooks/useResultadoVuelo'
import { etiquetaTipoCultivo } from '../utils/cultivos'
import MapaZonas from './MapaZonas'
import TablaZonas from './TablaZonas'
import TablaDiagnostico from './TablaDiagnostico'
import ModalPreviewPdf from './ModalPreviewPdf'

const SENSOR_LABELS = { sentinel2: 'Sentinel-2', dji_mavic3: 'DJI Mavic 3' }
const BANDA_LABELS = { BLUE: 'Azul', GREEN: 'Verde', RED: 'Rojo', RE: 'Red Edge', NIR: 'NIR' }

// Trazabilidad del análisis (HU-R4-02): qué archivo, quién lo subió y con qué
// parámetros se calculó — solo lectura, para justificar una prescripción ante
// el productor o un control según la Ley 6.312. metodo_umbral/mapeo_bandas
// quedan en null hasta que el worker termina de procesar el vuelo.
function PanelTrazabilidad({ vuelo }) {
  const bandas = vuelo.mapeo_bandas
    ? Object.entries(vuelo.mapeo_bandas)
        .filter(([, num]) => num != null)
        .map(([nombre, num]) => `${BANDA_LABELS[nombre] || nombre}: banda ${num}`)
        .join(' · ')
    : null

  return (
    <details className="trazabilidad-panel">
      <summary>Trazabilidad del análisis</summary>
      <dl className="trazabilidad-lista">
        <dt>Archivo de origen</dt>
        <dd>{vuelo.archivo_original || '—'}</dd>
        <dt>Subido por</dt>
        <dd>{vuelo.subido_por ? `${vuelo.subido_por.nombre} (${vuelo.subido_por.email})` : '—'}</dd>
        <dt>Fecha de subida</dt>
        <dd>{new Date(vuelo.created_at).toLocaleString('es-AR')}</dd>
        <dt>Mapeo de bandas ({SENSOR_LABELS[vuelo.sensor] || vuelo.sensor})</dt>
        <dd>{bandas || 'Sin calcular todavía'}</dd>
        <dt>Método de umbral</dt>
        <dd>{vuelo.metodo_umbral || 'Sin calcular todavía'}</dd>
      </dl>
    </details>
  )
}

// Un mapa + panel de Zonas/Diagnóstico completo para UN vuelo. Se usa una vez
// para el vuelo "principal" (el de la URL) y, en modo comparación, una
// segunda vez para el vuelo elegido desde "Seleccionar para comparar" — cada
// instancia carga y maneja sus propios datos de forma independiente.
export default function PanelResultadoVuelo({
  loteId, vueloId, vuelo, lote,
  esComparacion = false, onCerrarComparacion,
}) {
  const {
    zonas, loading, error,
    tab, setTab,
    diagnostico, diagnosticoLoading, diagnosticoError,
    recalculando, generandoOrden,
    previewPdf, cerrarPreviewPdf,
    handleRecalcular, handleGenerarOrdenTrabajo,
  } = useResultadoVuelo(loteId, vueloId, lote?.nombre)

  const [panelAbierto, setPanelAbierto] = useState(true)

  const features = zonas?.features || []

  const columnas = ['1fr', panelAbierto ? '340px' : '40px']

  return (
    <div className="resultados-panel">
      <div className="resultados-panel-encabezado">
        {vuelo?.cultivo && (
          <span className={`cultivo-badge cultivo-${vuelo.cultivo.tipo_cultivo}`}>
            {etiquetaTipoCultivo(vuelo.cultivo.tipo_cultivo)}
            {vuelo.cultivo.variedad ? ` · ${vuelo.cultivo.variedad}` : ''}
          </span>
        )}
        {vuelo && (
          <span className="pagina-encabezado-meta">
            <span className="resultados-panel-fecha">
              {new Date(vuelo.fecha_vuelo).toLocaleDateString('es-AR', { day: '2-digit', month: 'long', year: 'numeric' })}
            </span>
            {' · '}
            {SENSOR_LABELS[vuelo.sensor] || vuelo.sensor}
            {lote?.area_ha ? ` · ${lote.area_ha.toLocaleString('es-AR', { maximumFractionDigits: 1 })} ha` : ''}
          </span>
        )}
        {esComparacion && (
          <button
            type="button"
            className="resultados-panel-cerrar-comparacion"
            onClick={onCerrarComparacion}
            title="Cerrar comparación"
          >
            ✕ Comparación
          </button>
        )}
      </div>

      {vuelo && <PanelTrazabilidad vuelo={vuelo} />}

      {error ? (
        <p className="empty-hint">{error}</p>
      ) : (
        <main className="resultados-main" style={{ gridTemplateColumns: columnas.join(' ') }}>
          <div className="resultados-mapa">
            <MapaZonas geojson={zonas} diagnostico={tab === 'diagnostico' ? diagnostico : null} sinDatos={zonas?.sin_datos} />
            {loading && (
              <div className="resultados-mapa-overlay">
                <span className="diagnostico-spinner" />
              </div>
            )}
          </div>

          {panelAbierto ? (
            <div className="resultados-sidebar">
              <div className="resultados-tabs">
                <button
                  className={`resultados-tab ${tab === 'zonas' ? 'resultados-tab--activo' : ''}`}
                  onClick={() => setTab('zonas')}
                >
                  Zonas
                </button>
                <button
                  className={`resultados-tab ${tab === 'diagnostico' ? 'resultados-tab--activo' : ''}`}
                  onClick={() => setTab('diagnostico')}
                >
                  Diagnóstico
                </button>
                <div className="resultados-tabs-acciones">
                  <button
                    className="resultados-sidebar-cerrar"
                    onClick={() => setPanelAbierto(false)}
                    aria-label="Cerrar panel de zonas y diagnóstico"
                    title="Cerrar"
                  >
                    ×
                  </button>
                </div>
              </div>

              {tab === 'zonas' && !loading && (
                features.length > 0
                  ? <>
                      <TablaZonas features={features} />
                      <button className="link-diagnostico" onClick={() => setTab('diagnostico')}>
                        Ver diagnóstico agronómico →
                      </button>
                    </>
                  : <p className="empty-hint">Sin zonas clasificadas para este análisis.</p>
              )}

              {tab === 'diagnostico' && !loading && (
                <>
                  {diagnosticoLoading && (
                    <div className="diagnostico-loading">
                      <span className="diagnostico-spinner" />
                      <p>Analizando zonas y generando diagnóstico agronómico...</p>
                    </div>
                  )}
                  {diagnosticoError && <p className="empty-hint">{diagnosticoError}</p>}
                  {diagnostico && (
                    <TablaDiagnostico
                      diagnostico={diagnostico}
                      onRecalcular={handleRecalcular}
                      recalculando={recalculando}
                      onGenerarOrdenTrabajo={handleGenerarOrdenTrabajo}
                      generandoOrden={generandoOrden}
                    />
                  )}
                </>
              )}
            </div>
          ) : (
            <button
              type="button"
              className="resultados-sidebar-pestania"
              onClick={() => setPanelAbierto(true)}
              title="Ver zonas y diagnóstico"
            >
              Zonas y diagnóstico
            </button>
          )}
        </main>
      )}

      {previewPdf && (
        <ModalPreviewPdf
          titulo={previewPdf.titulo}
          blob={previewPdf.blob}
          filename={previewPdf.filename}
          onClose={cerrarPreviewPdf}
        />
      )}
    </div>
  )
}
