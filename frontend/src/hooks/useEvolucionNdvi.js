import { useEffect, useState } from 'react'
import { obtenerDiagnostico, obtenerNdviEsperado } from '../api/analisis'
import { buscarPuntoPorEstadio } from '../utils/estadios'

function idDe(vuelo) {
  return vuelo.vuelo_id ?? vuelo.id
}

function causasConProblema(features) {
  const causas = {}
  for (const f of features) {
    const p = f.properties || {}
    if (p.regla_id === 'R99' || p.regla_id === 'R00' || !p.causa_indice) continue
    // R01 (suelo desnudo) comparte causa_indice con R99 aunque sí es algo a revisar.
    const causa = p.regla_id === 'R01' ? 'suelo_desnudo' : p.causa_indice
    causas[causa] = (causas[causa] || 0) + (p.area_ha || 0)
  }
  return causas
}

// Evolución del NDVI del lote a lo largo de la campaña: un punto por vuelo
// completado (fecha del vuelo + ndvi_promedio_lote de su diagnóstico), para
// graficar la tendencia. Reusa GET /diagnostico (ya persiste el resultado la
// primera vez que se pide) en vez de traer un endpoint de serie temporal
// nuevo — mismo criterio que useResumenVuelo.
// Cada punto trae además el NDVI esperado para el estadio del vuelo (curva
// por cultivo de GET /estadios-fenologicos/ndvi-esperado) cuando el estadio
// cargado coincide con la curva, y las causas detectadas por el diagnóstico.
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

    const cultivos = [...new Set(completados.map(v => v.cultivo?.tipo_cultivo).filter(Boolean))]

    Promise.all([
      Promise.allSettled(completados.map(v => obtenerDiagnostico(loteId, idDe(v)))),
      Promise.allSettled(cultivos.map(c => obtenerNdviEsperado(c))),
    ])
      .then(([resultados, curvasRes]) => {
        if (cancelado) return

        const curvas = {}
        curvasRes.forEach((r, i) => {
          if (r.status === 'fulfilled') curvas[cultivos[i]] = r.value.puntos || []
        })

        const ok = resultados
          .map((r, i) => ({ r, vuelo: completados[i] }))
          .filter(({ r }) => r.status === 'fulfilled' && r.value?.metadata?.ndvi_promedio_lote != null)
          .map(({ r, vuelo }) => {
            const features = r.value.features || []
            const valores = features
              .map(f => f.properties?.ndvi_promedio)
              .filter(v => typeof v === 'number')
            const cultivo = vuelo.cultivo?.tipo_cultivo ?? null
            const esperado = buscarPuntoPorEstadio(curvas[cultivo], vuelo.estadio_fenologico)
            return {
              vueloId: idDe(vuelo),
              fecha: vuelo.fecha_vuelo,
              estadio: vuelo.estadio_fenologico,
              cultivo,
              ndviProm: r.value.metadata.ndvi_promedio_lote,
              ndviMin: valores.length > 0 ? Math.min(...valores) : null,
              ndviMax: valores.length > 0 ? Math.max(...valores) : null,
              esperado: esperado
                ? { valor: esperado.ndvi_esperado, min: esperado.ndvi_min, max: esperado.ndvi_max }
                : null,
              causas: causasConProblema(features),
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
