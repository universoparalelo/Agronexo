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
    // Solo un error sin `response` (conexión caída, timeout, CORS) es
    // transitorio y vale la pena reintentar en silencio. Un error CON
    // response (404 porque el vuelo/lote ya no existe, 500, etc.) nunca se
    // va a resolver solo reintentando — antes se lo trataba igual que uno
    // transitorio y el polling quedaba reintentando cada 2s para siempre,
    // sin mostrar nada (el análisis "no se mostraba", ver reporte de usuario).
    // Además, si los errores realmente transitorios se repiten demasiado
    // (backend caído, no solo un blip), tampoco tiene sentido quedar
    // reintentando en silencio de forma indefinida.
    let fallosDeRedSeguidos = 0
    const MAX_FALLOS_RED_SEGUIDOS = 5

    async function poll() {
      try {
        const { data } = await client.get(urlEstado)
        if (cancelled) return
        fallosDeRedSeguidos = 0
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
      } catch (err) {
        if (cancelled) return
        if (err?.response) {
          clearInterval(intervalRef.current)
          setErrorMsg(
            err.response.status === 404
              ? 'Este análisis ya no está disponible.'
              : 'No se pudo consultar el estado del análisis.'
          )
          return
        }
        // sin `response` → error de red transitorio, reintentar
        fallosDeRedSeguidos += 1
        if (fallosDeRedSeguidos >= MAX_FALLOS_RED_SEGUIDOS) {
          clearInterval(intervalRef.current)
          setErrorMsg('No se pudo conectar con el servidor. Revisá tu conexión e intentá de nuevo.')
        }
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
