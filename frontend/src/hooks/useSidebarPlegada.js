import { useSyncExternalStore } from 'react'

const CLAVE = 'agronexo.sidebarPlegada'

function leerGuardado() {
  try { return localStorage.getItem(CLAVE) === '1' } catch { return false }
}

// Estado compartido entre la barra lateral y el botón de la barra superior (son
// componentes distintos en cada pantalla) y recordado entre pantallas y recargas.
let plegada = leerGuardado()
const oyentes = new Set()

function suscribir(fn) {
  oyentes.add(fn)
  return () => oyentes.delete(fn)
}

export function alternarSidebar() {
  plegada = !plegada
  try { localStorage.setItem(CLAVE, plegada ? '1' : '0') } catch { /* sin almacenamiento: queda solo en memoria */ }
  oyentes.forEach((fn) => fn())
}

export default function useSidebarPlegada() {
  const valor = useSyncExternalStore(suscribir, () => plegada)
  return [valor, alternarSidebar]
}
