import { useSyncExternalStore } from 'react'
import { estadoConexion } from '../utils/conexion'

// true si hay internet. Mientras se hace la primera comprobación se asume que sí,
// para no mostrar el aviso de "sin conexión" al abrir la app.
export function useConexion() {
  return useSyncExternalStore(estadoConexion.suscribir, estadoConexion.obtener)
}
