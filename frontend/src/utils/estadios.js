// Espejo de app/diagnostico/estadios.py::normalizar_estadio — mismo criterio
// (minúsculas, sin acentos, espacios -> guión bajo) para poder comparar el
// texto libre de vuelo.estadio_fenologico contra la `etiqueta` que devuelve
// GET /estadios-fenologicos/ndvi-esperado sin pedirle al backend un endpoint
// de matching aparte.
export function normalizarEstadio(texto) {
  if (!texto) return null
  const sinAcentos = texto.normalize('NFKD').replace(/[̀-ͯ]/g, '')
  const normalizado = sinAcentos.trim().toLowerCase().replace(/\s+/g, '_')
  return normalizado || null
}

// Busca, dentro de la curva de un cultivo, el punto cuya etiqueta normalizada
// coincide con el estadio (texto libre) cargado en un vuelo.
export function buscarPuntoPorEstadio(puntos = [], estadioTexto) {
  const objetivo = normalizarEstadio(estadioTexto)
  if (!objetivo) return null
  return puntos.find((p) => normalizarEstadio(p.estadio) === objetivo) || null
}
