import { useEffect, useState } from 'react'
import useResultadoVuelo from '../hooks/useResultadoVuelo'
import { etiquetaTipoCultivo } from '../utils/cultivos'
import MapaZonas from './MapaZonas'
import TablaZonas from './TablaZonas'
import TablaDiagnostico from './TablaDiagnostico'
import TablaAhorroVuelo from './TablaAhorroVuelo'
import ModalCargarPrecio from './ModalCargarPrecio'
import ModalPreviewPdf from './ModalPreviewPdf'
import ModalMapaAmpliado from './ModalMapaAmpliado'

const SENSOR_LABELS = { sentinel2: 'Sentinel-2', dji_mavic3: 'DJI Mavic 3' }

// Un mapa + panel de Zonas/Diagnóstico completo para UN vuelo. Se usa una vez
// para el vuelo "principal" (el de la URL) y, en modo comparación, una
// segunda vez para el vuelo elegido desde "Seleccionar para comparar" — cada
// instancia carga y maneja sus propios datos de forma independiente.
export default function PanelResultadoVuelo({
  loteId, vueloId, vuelo, lote,
  esComparacion = false, onCerrarComparacion, onZonasCargadas, ocultarEncabezado = false,
}) {
  const {
    zonas, loading, error,
    tab, setTab,
    diagnostico, diagnosticoLoading, diagnosticoError,
    ahorro, ahorroLoading, ahorroError, recargarAhorro,
    generandoOrden,
    previewPdf, cerrarPreviewPdf,
    handleGenerarOrdenTrabajo,
  } = useResultadoVuelo(loteId, vueloId, lote?.nombre)

  const [mapaAmpliado, setMapaAmpliado] = useState(false)
  const [precioForm, setPrecioForm] = useState(null) // { productoId, nombre, unidad } | null
  // Avisa al padre (ResultadosVuelo) cada vez que cambian las zonas de este
  // panel — en modo comparación, cuando ambos paneles reportaron sus zonas
  // se puede calcular el resumen de diferencias entre los dos vuelos.
  useEffect(() => {
    onZonasCargadas?.(zonas)
  }, [zonas]) // eslint-disable-line react-hooks/exhaustive-deps

  const features = zonas?.features || []

  const renderMapa = ({ clase = '', agrandar = true } = {}) => (
    <div className={`resultados-mapa ${clase}`.trim()}>
      <MapaZonas geojson={zonas} diagnostico={tab === 'diagnostico' ? diagnostico : null} sinDatos={zonas?.sin_datos} leyendaHorizontal />
      {agrandar && (
        <button
          type="button"
          className="resultados-mapa-agrandar"
          onClick={() => setMapaAmpliado(true)}
          title="Agrandar mapa"
          aria-label="Agrandar mapa"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>
            <line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
          </svg>
        </button>
      )}
      {loading && (
        <div className="resultados-mapa-overlay">
          <span className="diagnostico-spinner" />
        </div>
      )}
    </div>
  )

  const panelZonasDiagnostico = (
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
        <button
          className={`resultados-tab ${tab === 'ahorro' ? 'resultados-tab--activo' : ''}`}
          onClick={() => setTab('ahorro')}
        >
          Ahorro comparativo
        </button>
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

      {tab === 'ahorro' && !loading && (
        <>
          {ahorroLoading && (
            <div className="diagnostico-loading">
              <span className="diagnostico-spinner" />
              <p>Calculando el ahorro...</p>
            </div>
          )}
          {ahorroError && <p className="empty-hint">{ahorroError}</p>}
          {ahorro && (
            <TablaAhorroVuelo
              ahorro={ahorro}
              onCargarPrecio={(productoId, nombre, unidad) => setPrecioForm({ productoId, nombre, unidad })}
            />
          )}
        </>
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
              onGenerarOrdenTrabajo={handleGenerarOrdenTrabajo}
              generandoOrden={generandoOrden}
            />
          )}
        </>
      )}

    </div>
  )

  const cuerpo = error
    ? <p className="empty-hint">{error}</p>
    : (
      <main className="resultados-main resultados-main--dividida">
        {renderMapa({ clase: esComparacion ? 'es-comparacion' : '' })}
        {panelZonasDiagnostico}
      </main>
    )

  return (
    <div className="resultados-panel">
      {!ocultarEncabezado && (
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
      )}

      {cuerpo}

      {mapaAmpliado && (
        <ModalMapaAmpliado titulo={lote?.nombre ? `Mapa — ${lote.nombre}` : 'Mapa del lote'} onClose={() => setMapaAmpliado(false)}>
          <MapaZonas geojson={zonas} diagnostico={tab === 'diagnostico' ? diagnostico : null} sinDatos={zonas?.sin_datos} leyendaHorizontal />
        </ModalMapaAmpliado>
      )}

      {precioForm && (
        <ModalCargarPrecio
          productoId={precioForm.productoId}
          productoNombre={precioForm.nombre}
          unidadSugerida={precioForm.unidad}
          onClose={() => setPrecioForm(null)}
          onGuardado={() => { setPrecioForm(null); recargarAhorro() }}
        />
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
