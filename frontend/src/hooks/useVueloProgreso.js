import { useState, useEffect, useRef } from 'react'
import client from '../api/client'

// absorber: pide la versión resumida del resultado (lo que tiene datos pero no quedó con zona se
// combina con la zona vecina), para mapas de vistazo. El `sin_datos` real viene siempre en el resultado.
export function useVueloProgreso(loteId, vueloId, indice = 'ndvi', { absorber = false } = {}) {
  const [estado, setEstado] = useState(null)
  const [geojson, setGeojson] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    setEstado(null)
    setGeojson(null)
    setErrorMsg(null)

    if (!loteId || !vueloId) return

    // NDVI (el índice "primario") vive en los endpoints del vuelo mismo;
    // el resto de los índices (NDRE/SAVI/ExG) en el sub-recurso /indices/{indice}.
    const base = `/lotes/${loteId}/vuelos/${vueloId}`
    const urlEstado = !indice || indice === 'ndvi' ? `${base}/estado` : `${base}/indices/${indice}/estado`
    const urlResultado = (!indice || indice === 'ndvi' ? `${base}/resultado` : `${base}/indices/${indice}/resultado`)
      + (absorber ? '?absorber=true' : '')

    let cancelled = false

    async function poll() {
      try {
        const { data } = await client.get(urlEstado)
        if (cancelled) return
        setEstado(data)

        if (data.estado === 'completado') {
          clearInterval(intervalRef.current)
          try {
            const { data: gj } = await client.get(urlResultado)
            if (!cancelled) setGeojson(gj)
          } catch {
            if (!cancelled) setErrorMsg('No se pudo cargar el resultado del análisis.')
          }
        } else if (data.estado === 'error') {
          clearInterval(intervalRef.current)
          if (!cancelled) setErrorMsg(data.error ?? 'El procesamiento falló.')
        }
      } catch {
        // error de red transitorio — mantener polling
      }
    }

    poll()
    intervalRef.current = setInterval(poll, 2000)

    return () => {
      cancelled = true
      clearInterval(intervalRef.current)
    }
  }, [loteId, vueloId, indice, absorber])

  return { estado, geojson, errorMsg }
}
