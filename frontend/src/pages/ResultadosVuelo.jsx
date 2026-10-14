import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import client from '../api/client'
import BotonVolver from '../components/BotonVolver'
import PanelLayout from '../components/PanelLayout'
import PanelResultadoVuelo from '../components/PanelResultadoVuelo'
import ResumenDiferenciaVuelos from '../components/ResumenDiferenciaVuelos'
import VuelosCalendario from '../components/VuelosCalendario'
import ModalCargaGeoTIFF from '../components/ModalCargaGeoTIFF'

function idDe(vuelo) {
  return vuelo.vuelo_id ?? vuelo.id
}

export default function ResultadosVuelo() {
  const { loteId, vueloId } = useParams()
  const navigate = useNavigate()

  const [lote, setLote]     = useState(null)
  const [vuelos, setVuelos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  const [vueloComparacionId, setVueloComparacionId] = useState(null)
  const [calendarioAbierto, setCalendarioAbierto] = useState(false)
  const [nuevoAnalisisAbierto, setNuevoAnalisisAbierto] = useState(false)

  // Zonas de cada panel, reportadas por PanelResultadoVuelo vía onZonasCargadas
  // — cuando las dos están listas se puede calcular el resumen de diferencias.
  const [zonasPrincipal, setZonasPrincipal] = useState(null)
  const [zonasComparacion, setZonasComparacion] = useState(null)

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
  }, [vueloComparacionId])

  if (loading && !lote) return <div className="page-loading">Cargando resultados...</div>

  if (error) return (
    <div className="page-error">
      <p>{error}</p>
      <BotonVolver to={`/lotes/${loteId}`} claro>Volver a los vuelos</BotonVolver>
    </div>
  )

  const vueloPrincipal = vuelos.find(v => idDe(v) === vueloId) || null
  const vueloComparacion = vueloComparacionId ? vuelos.find(v => idDe(v) === vueloComparacionId) || null : null

  return (
    <PanelLayout
      alto
      migas={[
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Lotes', to: '/lotes' },
        { label: lote?.nombre ?? 'Lote', to: `/lotes/${loteId}` },
        { label: 'Resultados' },
      ]}
      onVerDiagnosticos={() => navigate(`/lotes/${loteId}`)}
    >
      <div className="resultados-shell">
        <div className="pagina-encabezado">
          <h1>{lote?.nombre}</h1>
          <button
            type="button"
            className="resultados-vuelos-boton"
            onClick={() => setCalendarioAbierto(true)}
            title="Ver vuelos del lote en un calendario"
          >
            📅 Vuelos
          </button>
        </div>

        {vueloComparacionId && vueloPrincipal && vueloComparacion && zonasPrincipal && zonasComparacion && (
          <ResumenDiferenciaVuelos
            vueloA={vueloPrincipal}
            vueloB={vueloComparacion}
            featuresA={zonasPrincipal.features || []}
            featuresB={zonasComparacion.features || []}
          />
        )}

        <div className={`resultados-comparacion ${vueloComparacionId ? 'resultados-comparacion--activa' : ''}`}>
          <PanelResultadoVuelo
            loteId={loteId}
            vueloId={vueloId}
            vuelo={vueloPrincipal}
            lote={lote}
            onZonasCargadas={setZonasPrincipal}
          />

          {vueloComparacionId && (
            <PanelResultadoVuelo
              key={vueloComparacionId}
              loteId={loteId}
              vueloId={vueloComparacionId}
              vuelo={vueloComparacion}
              lote={lote}
              esComparacion
              onCerrarComparacion={() => setVueloComparacionId(null)}
              onZonasCargadas={setZonasComparacion}
            />
          )}
        </div>
      </div>

      {calendarioAbierto && (
        <div className="resultados-calendario-overlay" onClick={() => setCalendarioAbierto(false)}>
          <div className="resultados-calendario-panel" onClick={(e) => e.stopPropagation()}>
            <VuelosCalendario
              loteId={loteId}
              vuelos={vuelos}
              vueloActualId={vueloId}
              onCerrar={() => setCalendarioAbierto(false)}
              onComparar={(v) => { setVueloComparacionId(idDe(v)); setCalendarioAbierto(false) }}
              onNuevoAnalisis={() => { setCalendarioAbierto(false); setNuevoAnalisisAbierto(true) }}
            />
          </div>
        </div>
      )}

      {nuevoAnalisisAbierto && (
        <ModalCargaGeoTIFF
          lotes={lote ? [lote] : []}
          loteIdInicial={loteId}
          loteFijo
          onSuccess={() => { setNuevoAnalisisAbierto(false); cargarLoteYVuelos() }}
          onClose={() => setNuevoAnalisisAbierto(false)}
        />
      )}
    </PanelLayout>
  )
}
