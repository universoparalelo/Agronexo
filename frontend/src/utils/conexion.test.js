import { describe, it, expect, vi } from 'vitest'
import {
  crearEstadoConexion, haySalidaAInternet, REPETIR_CON_CONEXION_MS, REPETIR_SIN_CONEXION_MS,
} from './conexion'

describe('haySalidaAInternet', () => {
  it('hay conexión si el servidor contesta', async () => {
    expect(await haySalidaAInternet(async () => ({}))).toBe(true)
  })

  it('no hay conexión si la consulta falla', async () => {
    expect(await haySalidaAInternet(async () => { throw new TypeError('Failed to fetch') })).toBe(false)
  })

  it('no hay conexión si el servidor no contesta a tiempo', async () => {
    const colgado = (_url, { signal }) => new Promise((_ok, no) => {
      signal.addEventListener('abort', () => no(new DOMException('abort', 'AbortError')))
    })
    expect(await haySalidaAInternet(colgado, 'https://x.test', 20)).toBe(false)
  })

  it('el aviso del sistema de que no hay red alcanza, sin consultar nada', async () => {
    vi.stubGlobal('navigator', { onLine: false })
    const consulta = vi.fn()
    expect(await haySalidaAInternet(consulta)).toBe(false)
    expect(consulta).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
})

function estadoDePrueba(respuestas) {
  const pendientes = []
  const sondear = vi.fn(async () => respuestas.shift())
  const estado = crearEstadoConexion({
    sondear,
    programar: (fn, ms) => { pendientes.push({ fn, ms }); return pendientes.length },
    cancelar: vi.fn(),
  })
  return { estado, sondear, pendientes }
}

const esperarComprobacion = () => new Promise((r) => setTimeout(r, 0))

describe('estado de la conexión', () => {
  it('arranca asumiendo que hay conexión', () => {
    const { estado } = estadoDePrueba([true])
    expect(estado.obtener()).toBe(true)
  })

  it('avisa a los suscriptores cuando se pierde la conexión', async () => {
    const { estado } = estadoDePrueba([false])
    const oyente = vi.fn()
    const baja = estado.suscribir(oyente)
    await esperarComprobacion()
    expect(estado.obtener()).toBe(false)
    expect(oyente).toHaveBeenCalledTimes(1)
    baja()
  })

  it('no avisa si el estado no cambió', async () => {
    const { estado } = estadoDePrueba([true])
    const oyente = vi.fn()
    const baja = estado.suscribir(oyente)
    await esperarComprobacion()
    expect(oyente).not.toHaveBeenCalled()
    baja()
  })

  it('vuelve a comprobar antes sin conexión que con conexión', async () => {
    const sin = estadoDePrueba([false])
    const bajaSin = sin.estado.suscribir(() => {})
    await esperarComprobacion()
    expect(sin.pendientes.at(-1).ms).toBe(REPETIR_SIN_CONEXION_MS)
    bajaSin()

    const con = estadoDePrueba([true])
    const bajaCon = con.estado.suscribir(() => {})
    await esperarComprobacion()
    expect(con.pendientes.at(-1).ms).toBe(REPETIR_CON_CONEXION_MS)
    bajaCon()
  })

  it('detecta que volvió internet en la comprobación siguiente', async () => {
    const { estado, pendientes } = estadoDePrueba([false, true])
    const oyente = vi.fn()
    const baja = estado.suscribir(oyente)
    await esperarComprobacion()
    pendientes.at(-1).fn()
    await esperarComprobacion()
    expect(estado.obtener()).toBe(true)
    expect(oyente).toHaveBeenCalledTimes(2)
    baja()
  })

  it('una sola comprobación aunque haya varios suscriptores, y se detiene al irse el último', async () => {
    const { estado, sondear } = estadoDePrueba([true, true])
    const baja1 = estado.suscribir(() => {})
    const baja2 = estado.suscribir(() => {})
    await esperarComprobacion()
    expect(sondear).toHaveBeenCalledTimes(1)
    baja1()
    baja2()
    expect(sondear).toHaveBeenCalledTimes(1)
  })
})
