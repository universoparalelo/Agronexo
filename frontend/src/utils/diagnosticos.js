import { listarVuelos } from '../api/analisis'

// Lleva al diagnóstico del último vuelo completado del lote; si no tiene ninguno, a su lista de vuelos.
export async function irAlUltimoDiagnostico(navigate, loteId) {
  try {
    const vuelos = await listarVuelos(loteId)
    const ultimo = vuelos
      .filter(v => v.estado === 'completado')
      .sort((a, b) => new Date(b.fecha_vuelo) - new Date(a.fecha_vuelo))[0]
    if (ultimo) {
      navigate(`/lotes/${loteId}/vuelos/${ultimo.vuelo_id}`)
      return
    }
  } catch {
    // si no se pueden leer los vuelos, la lista del lote los vuelve a pedir y muestra el error
  }
  navigate(`/lotes/${loteId}`)
}
