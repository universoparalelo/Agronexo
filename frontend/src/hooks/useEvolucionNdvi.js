import { useEffect, useState } from 'react'
import { obtenerDiagnostico } from '../api/analisis'

function idDe(vuelo) {
  return vuelo.vuelo_id ?? vuelo.id
}

// Evolución del NDVI del lote a lo largo de la campaña: un punto por vuelo
// completado (fecha del vuelo + ndvi_promedio_lote de su diagnóstico), para
// graficar la tendencia. Reusa GET /diagnostico (ya persiste el resultado la
// primera vez que se pide) en vez de traer un endpoint de serie temporal
// nuevo — mismo criterio que useResumenVuelo.
export default function useEvolucionNdvi(loteId, vuelos) {
  const [puntos, setPuntos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const completados = vuelos.filter(v => v.estado === 'completado')
    if (completados.length === 0) {
      setPuntos([])
      setLoading(false)
      return
    }

    let cancelado = false
    setLoading(true)
    setError('')

    Promise.allSettled(completados.map(v => obtenerDiagnostico(loteId, idDe(v))))
      .then((resultados) => {
        if (cancelado) return

        const ok = resultados
          .map((r, i) => ({ r, vuelo: completados[i] }))
          .filter(({ r }) => r.status === 'fulfilled' && r.value?.metadata?.ndvi_promedio_lote != null)
          .map(({ r, vuelo }) => {
            const features = r.value.features || []
            const valores = features
              .map(f => f.properties?.ndvi_promedio)
              .filter(v => typeof v === 'number')
            return {
              vueloId: idDe(vuelo),
              fecha: vuelo.fecha_vuelo,
              estadio: vuelo.estadio_fenologico,
              ndviProm: r.value.metadata.ndvi_promedio_lote,
              ndviMin: valores.length > 0 ? Math.min(...valores) : null,
              ndviMax: valores.length > 0 ? Math.max(...valores) : null,
            }
          })
          .sort((a, b) => new Date(a.fecha) - new Date(b.fecha))

        setPuntos(ok)
        if (ok.length === 0 && completados.length > 0) {
          setError('No se pudo calcular la evolución de NDVI para los vuelos de este lote.')
        }
      })
      .finally(() => { if (!cancelado) setLoading(false) })

    return () => { cancelado = true }
  }, [loteId, vuelos])

  return { puntos, loading, error }
}
