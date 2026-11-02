// Detecta si hay internet de verdad. `navigator.onLine` solo dice si hay una red
// conectada (aunque esa red no salga a internet), así que además se hace una
// consulta liviana a un servidor de comprobación de conexión.
export const URL_SONDA = 'https://www.gstatic.com/generate_204'
export const ESPERA_SONDA_MS = 6000
export const REPETIR_SIN_CONEXION_MS = 30_000
export const REPETIR_CON_CONEXION_MS = 5 * 60_000

export async function haySalidaAInternet(fetchFn = fetch, url = URL_SONDA, espera = ESPERA_SONDA_MS) {
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return false
  const control = new AbortController()
  const reloj = setTimeout(() => control.abort(), espera)
  try {
    // no-cors: no se lee la respuesta, alcanza con que el servidor conteste
    await fetchFn(url, { mode: 'no-cors', cache: 'no-store', signal: control.signal })
    return true
  } catch {
    return false
  } finally {
    clearTimeout(reloj)
  }
}

// Estado compartido por toda la app: una sola comprobación para todos los mapas
// y botones, no una por componente.
export function crearEstadoConexion({
  sondear = haySalidaAInternet,
  programar = setTimeout,
  cancelar = clearTimeout,
} = {}) {
  let hayConexion = true
  let reloj = null
  let activo = false
  const oyentes = new Set()

  function fijar(valor) {
    if (valor === hayConexion) return
    hayConexion = valor
    oyentes.forEach((o) => o())
  }

  async function comprobar() {
    if (!activo) return
    fijar(await sondear())
    if (!activo) return
    reloj = programar(comprobar, hayConexion ? REPETIR_CON_CONEXION_MS : REPETIR_SIN_CONEXION_MS)
  }

  function recomprobar() {
    if (!activo) return
    cancelar(reloj)
    comprobar()
  }

  function iniciar() {
    activo = true
    if (typeof window !== 'undefined') {
      window.addEventListener('online', recomprobar)
      window.addEventListener('offline', recomprobar)
    }
    comprobar()
  }

  function detener() {
    activo = false
    cancelar(reloj)
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', recomprobar)
      window.removeEventListener('offline', recomprobar)
    }
  }

  return {
    obtener: () => hayConexion,
    suscribir(oyente) {
      oyentes.add(oyente)
      if (oyentes.size === 1) iniciar()
      return () => {
        oyentes.delete(oyente)
        if (oyentes.size === 0) detener()
      }
    },
  }
}

export const estadoConexion = crearEstadoConexion()
