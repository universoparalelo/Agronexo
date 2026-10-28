import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import client from '../api/client'
import { obtenerDiagnostico } from '../api/analisis'
import { etiquetaTipoCultivo } from '../utils/cultivos'
import BotonVolver from '../components/BotonVolver'
import PanelLayout from '../components/PanelLayout'
import PanelResultadoVuelo from '../components/PanelResultadoVuelo'
import ResumenDiferenciaVuelos from '../components/ResumenDiferenciaVuelos'
import MapaComparacionLote from '../components/MapaComparacionLote'
import SelectorVuelo from '../components/SelectorVuelo'
import ModalCompararVuelos from '../components/ModalCompararVuelos'

const SENSOR_LABELS = { sentinel2: 'Sentinel-2', dji_mavic3: 'DJI Mavic 3' }

function idDe(vuelo) {
  return vuelo.vuelo_id ?? vuelo.id
}

export default function ResultadosVuelo() {
  const { loteId, vueloId } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [lote, setLote]     = useState(null)
  const [vuelos, setVuelos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  // `?comparar=<vuelo>` abre la pantalla ya comparando (viene del botón "Comparar vuelos" del lote).
  const [vueloComparacionId, setVueloComparacionId] = useState(searchParams.get('comparar'))
  const [compararAbierto, setCompararAbierto] = useState(false)
  // Una sola forma de ver el mapa a la vez: 'completa' (los dos paneles
  // enteros, con sidebar de Zonas/Diagnóstico — el default y lo único que
  // existe sin comparación activa), 'lado-a-lado' o 'cortina'.
  const [vistaMapa, setVistaMapa] = useState('completa')

  // Zonas de cada panel, reportadas por PanelResultadoVuelo vía onZonasCargadas
  // — cuando las dos están listas se puede calcular el resumen de diferencias.
  const [zonasPrincipal, setZonasPrincipal] = useState(null)
  const [zonasComparacion, setZonasComparacion] = useState(null)
  // Diagnóstico del vuelo principal, solo para mostrar la causa por zona en
  // "Cambio por zona" — PanelResultadoVuelo lo pide perezoso (al entrar al
  // tab "Diagnóstico"), así que acá se pide aparte apenas arranca una
  // comparación, sin esperar a que el usuario abra ese tab en el panel.
  const [diagnosticoPrincipal, setDiagnosticoPrincipal] = useState(null)

  function cerrarComparacion() {
    navigate(`/lotes/${loteId}`)
  }

  const irAVuelo = (id) => navigate(`/lotes/${loteId}/vuelos/${id}`)
  const cambiarVueloBase = (id) => navigate(`/lotes/${loteId}/vuelos/${id}?comparar=${vueloComparacionId}`, { replace: true })
  const cambiarVueloComparado = (id) => {
    setVueloComparacionId(id)
    navigate(`/lotes/${loteId}/vuelos/${vueloId}?comparar=${id}`, { replace: true })
  }
  function comenzarComparacion(anteriorId, posteriorId) {
    setCompararAbierto(false)
    setVueloComparacionId(posteriorId)
    navigate(`/lotes/${loteId}/vuelos/${anteriorId}?comparar=${posteriorId}`)
  }

  function cargarLoteYVuelos() {
    setLoading(true)
    setError('')
    return Promise.all([
      client.get(`/lotes/${loteId}`).then(r => r.data),
      client.get(`/lotes/${loteId}/vuelos`).then(r => r.data),
    ])
      .then(([loteData, vuelosData]) => {
        setLote(loteData)
        setVuelos(vuelosData)
      })
      .catch(() => setError('No se pudieron cargar los resultados del análisis.'))
      .finally(() => setLoading(false))
  }

  // lote + lista de vuelos no dependen del vuelo que se está viendo — se
  // piden una sola vez por lote, no cada vez que cambia vueloId.
  useEffect(() => {
    cargarLoteYVuelos()
  }, [loteId]) // eslint-disable-line react-hooks/exhaustive-deps

  // No tiene sentido comparar un vuelo contra sí mismo — si el usuario navega
  // el panel principal hasta llegar al que ya estaba eligió para comparar,
  // se cierra solo.
  useEffect(() => {
    if (vueloComparacionId === vueloId) setVueloComparacionId(null)
  }, [vueloId, vueloComparacionId])

  // El panel de comparación se remonta (key={vueloComparacionId}) cada vez
  // que cambia el vuelo elegido — las zonas viejas se descartan acá para no
  // mostrar un resumen de diferencias con datos del vuelo anterior mientras
  // carga el nuevo.
  useEffect(() => {
    setZonasComparacion(null)
    setVistaMapa('completa')
  }, [vueloComparacionId])

  useEffect(() => {
    if (!vueloComparacionId || !loteId || !vueloId) { setDiagnosticoPrincipal(null); return }
    let cancelado = false
    obtenerDiagnostico(loteId, vueloId)
      .then((data) => { if (!cancelado) setDiagnosticoPrincipal(data) })
      .catch(() => { if (!cancelado) setDiagnosticoPrincipal(null) })
    return () => { cancelado = true }
  }, [vueloComparacionId, loteId, vueloId])

  if (loading && !lote) return <div className="page-loading">Cargando resultados...</div>

  if (error) return (
    <div className="page-error">
      <p>{error}</p>
      <BotonVolver to={`/lotes/${loteId}`} claro>Volver a los vuelos</BotonVolver>
    </div>
  )

  const vuelosCompletados = vuelos.filter(v => v.estado === 'completado')
  const vueloPrincipal = vuelos.find(v => idDe(v) === vueloId) || null
  const vueloComparacion = vueloComparacionId ? vuelos.find(v => idDe(v) === vueloComparacionId) || null : null

  return (
    <PanelLayout
      alto
      migas={[
        { label: 'Lotes', to: '/lotes' },
        { label: lote?.nombre ?? 'Lote', to: `/lotes/${loteId}` },
        { label: 'Resultados' },
      ]}
    >
      <div className={`resultados-shell${!vueloComparacionId ? ' resultados-shell--fija' : ''}`}>
        <div className="detalle-cabecera">
          <div>
            <div className="detalle-titulo-fila">
              <h1>{vueloComparacionId ? 'Comparación de vuelos' : lote?.nombre}</h1>
              {vueloComparacionId && lote?.nombre && <span className="lote-etiqueta">{lote.nombre}</span>}
            </div>
            {vueloComparacionId && (
              <div className="detalle-subtitulo">
                {vueloPrincipal?.cultivo && <span>{etiquetaTipoCultivo(vueloPrincipal.cultivo.tipo_cultivo)}</span>}
                {lote?.area_ha ? <span>{lote.area_ha.toLocaleString('es-AR', { maximumFractionDigits: 1 })} ha</span> : null}
              </div>
            )}
            {!vueloComparacionId && vueloPrincipal && (
              <div className="detalle-subtitulo">
                {vueloPrincipal.cultivo && (
                  <span className={`cultivo-badge cultivo-${vueloPrincipal.cultivo.tipo_cultivo}`}>
                    {etiquetaTipoCultivo(vueloPrincipal.cultivo.tipo_cultivo)}
                    {vueloPrincipal.cultivo.variedad ? ` · ${vueloPrincipal.cultivo.variedad}` : ''}
                  </span>
                )}
                <SelectorVuelo vuelos={vuelosCompletados} valor={vueloId} onCambiar={irAVuelo} />
                <span>{SENSOR_LABELS[vueloPrincipal.sensor] || vueloPrincipal.sensor}</span>
                {lote?.area_ha ? <span>{lote.area_ha.toLocaleString('es-AR', { maximumFractionDigits: 1 })} ha</span> : null}
                {vueloPrincipal.estadio_fenologico && <span className="vuelo-estadio-tag" title="Estadio fenológico">{vueloPrincipal.estadio_fenologico}</span>}
                <span className="indices-usados">
                  {(vueloPrincipal.indices || []).filter((i) => i.estado === 'completado').map((i) => (
                    <span key={i.indice} className="vuelo-estadio-tag" title="Índice usado en el diagnóstico">{i.indice.toUpperCase()}</span>
                  ))}
                </span>
              </div>
            )}
          </div>
          <div className="detalle-cabecera-acciones">
            {vueloComparacionId && (
              <div className="vista-mapa-tabs">
                <button
                  type="button"
                  className={`mapa-comparacion-tab ${vistaMapa === 'completa' ? 'mapa-comparacion-tab--activo' : ''}`}
                  onClick={() => setVistaMapa('completa')}
                >
                  Vista completa
                </button>
                <button
                  type="button"
                  className={`mapa-comparacion-tab ${vistaMapa === 'lado-a-lado' ? 'mapa-comparacion-tab--activo' : ''}`}
                  onClick={() => setVistaMapa('lado-a-lado')}
                >
                  Lado a lado
                </button>
                <button
                  type="button"
                  className={`mapa-comparacion-tab ${vistaMapa === 'cortina' ? 'mapa-comparacion-tab--activo' : ''}`}
                  onClick={() => setVistaMapa('cortina')}
                >
                  Cortina
                </button>
              </div>
            )}
            {vueloComparacionId && (
              <button
                type="button"
                className="btn-secondary btn-cerrar-comparacion"
                onClick={cerrarComparacion}
                title="Volver a la página del lote"
              >
                ✕ Cerrar comparación
              </button>
            )}
            {!vueloComparacionId && (
              <button
                type="button"
                className="btn-secondary"
                disabled={vuelosCompletados.length < 2}
                onClick={() => setCompararAbierto(true)}
                title={vuelosCompletados.length < 2 ? 'Hace falta otro vuelo completado para comparar' : 'Comparar dos vuelos del lote'}
              >
                Comparar vuelos
              </button>
            )}
          </div>
        </div>

        {/* Los dos paneles quedan siempre montados (cada uno pide sus propias
            zonas) aunque no se estén mostrando, para no re-pedirlas cada vez
            que se cambia de pestaña — "Lado a lado"/"Cortina" dependen de
            esos mismos datos. */}
        <div
          className={`resultados-comparacion ${vueloComparacionId ? 'resultados-comparacion--activa' : ''}`}
          style={vistaMapa === 'completa' ? undefined : { display: 'none' }}
        >
          <PanelResultadoVuelo
            loteId={loteId}
            vueloId={vueloId}
            vuelo={vueloPrincipal}
            lote={lote}
            ocultarEncabezado={!vueloComparacionId}
            onZonasCargadas={setZonasPrincipal}
            vuelosDisponibles={vuelosCompletados}
            excluirVueloId={vueloComparacionId}
            onCambiarVuelo={cambiarVueloBase}
          />

          {vueloComparacionId && (
            <PanelResultadoVuelo
              key={vueloComparacionId}
              loteId={loteId}
              vueloId={vueloComparacionId}
              vuelo={vueloComparacion}
              lote={lote}
              esComparacion
              onZonasCargadas={setZonasComparacion}
              vuelosDisponibles={vuelosCompletados}
              excluirVueloId={vueloId}
              onCambiarVuelo={cambiarVueloComparado}
            />
          )}
        </div>

        {vueloComparacionId && vistaMapa !== 'completa' && vueloPrincipal && vueloComparacion && zonasPrincipal && zonasComparacion && (
          <MapaComparacionLote
            vueloA={vueloPrincipal}
            vueloB={vueloComparacion}
            featuresA={zonasPrincipal.features || []}
            featuresB={zonasComparacion.features || []}
            tab={vistaMapa}
          />
        )}

        {vueloComparacionId && vueloPrincipal && vueloComparacion && zonasPrincipal && zonasComparacion && (
          <ResumenDiferenciaVuelos
            vueloA={vueloPrincipal}
            vueloB={vueloComparacion}
            featuresA={zonasPrincipal.features || []}
            featuresB={zonasComparacion.features || []}
            diagnosticoA={diagnosticoPrincipal}
            lote={lote}
          />
        )}
      </div>

      {compararAbierto && (
        <ModalCompararVuelos
          vuelos={vuelosCompletados}
          onComparar={comenzarComparacion}
          onClose={() => setCompararAbierto(false)}
        />
      )}
    </PanelLayout>
  )
}
