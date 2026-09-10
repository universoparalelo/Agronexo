export const AREA_MIN_HA = 0.5
export const AREA_MAX_HA = 5000

// Fórmula de exceso esférico — misma usada por Leaflet.draw GeometryUtil.geodesicArea,
// necesaria porque leaflet-geoman-free no expone un helper de área geodésica propio.
// Recibe un anillo de puntos {lat, lng} (formato de Leaflet), cerrado o no.
export function areaGeodesicaM2(latlngs) {
  const R = 6378137
  let area = 0
  const n = latlngs.length
  for (let i = 0; i < n; i++) {
    const p1 = latlngs[i]
    const p2 = latlngs[(i + 1) % n]
    area +=
      ((p2.lng - p1.lng) * Math.PI) / 180 *
      (2 + Math.sin((p1.lat * Math.PI) / 180) + Math.sin((p2.lat * Math.PI) / 180))
  }
  return Math.abs((area * R * R) / 2)
}

function orientacion(o, a, b) {
  return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
}

function dentroDeSegmento(p, q, r) {
  return (
    Math.min(p[0], r[0]) <= q[0] && q[0] <= Math.max(p[0], r[0]) &&
    Math.min(p[1], r[1]) <= q[1] && q[1] <= Math.max(p[1], r[1])
  )
}

function segmentosSeCruzan(p1, p2, p3, p4) {
  const d1 = orientacion(p3, p4, p1)
  const d2 = orientacion(p3, p4, p2)
  const d3 = orientacion(p1, p2, p3)
  const d4 = orientacion(p1, p2, p4)

  if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) {
    return true
  }
  if (d1 === 0 && dentroDeSegmento(p3, p1, p4)) return true
  if (d2 === 0 && dentroDeSegmento(p3, p2, p4)) return true
  if (d3 === 0 && dentroDeSegmento(p1, p3, p2)) return true
  if (d4 === 0 && dentroDeSegmento(p1, p4, p2)) return true
  return false
}

// Chequeo O(n²) de autointersección entre aristas no adyacentes de un anillo
// GeoJSON (cerrado: coords[0] === coords[n-1]). Suficiente para polígonos de
// lote, que tienen pocos vértices — evita sumar una dependencia como turf
// solo para esta validación.
export function tieneAutointerseccion(coordenadasAnillo) {
  const n = coordenadasAnillo.length - 1
  if (n < 4) return false
  for (let i = 0; i < n; i++) {
    const a1 = coordenadasAnillo[i]
    const a2 = coordenadasAnillo[i + 1]
    for (let j = i + 1; j < n; j++) {
      const sonAdyacentes = j === i + 1 || (i === 0 && j === n - 1)
      if (sonAdyacentes) continue
      const b1 = coordenadasAnillo[j]
      const b2 = coordenadasAnillo[j + 1]
      if (segmentosSeCruzan(a1, a2, b1, b2)) return true
    }
  }
  return false
}
