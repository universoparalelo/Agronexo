// Emparejamiento de zonas entre dos vuelos del mismo lote (HU-R4-09): cada
// análisis vectoriza sus propias zonas de forma independiente, así que no hay
// un id compartido entre vuelos — se empareja por posición (centroide de la
// zona "base" cae dentro de una zona del otro vuelo). Sin turf, mismo criterio
// que utils/geometria.js: polígonos de pocas zonas, no justifica la dependencia.

function anillosDe(geometry) {
  if (!geometry) return []
  if (geometry.type === 'Polygon') return geometry.coordinates
  if (geometry.type === 'MultiPolygon') return geometry.coordinates.flat()
  return []
}

export function bboxDeGeometrias(geometrias) {
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity
  for (const geom of geometrias) {
    for (const anillo of anillosDe(geom)) {
      for (const [lon, lat] of anillo) {
        if (lon < minLon) minLon = lon
        if (lon > maxLon) maxLon = lon
        if (lat < minLat) minLat = lat
        if (lat > maxLat) maxLat = lat
      }
    }
  }
  if (minLon === Infinity) return null
  return { minLon, minLat, maxLon, maxLat }
}

// Centroide simple (promedio de vértices del anillo exterior) — suficiente
// para decidir en qué zona del otro vuelo cae, no se usa para área.
export function centroideDe(geometry) {
  const anillo = anillosDe(geometry)[0]
  if (!anillo || anillo.length === 0) return null
  let sumLon = 0, sumLat = 0
  for (const [lon, lat] of anillo) { sumLon += lon; sumLat += lat }
  return [sumLon / anillo.length, sumLat / anillo.length]
}

// Ray casting (even-odd) sobre todos los anillos de la geometría — sirve para
// Polygon y MultiPolygon por igual tratando cada anillo como un polígono simple.
function puntoEnAnillo([lon, lat], anillo) {
  let dentro = false
  for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
    const [loni, lati] = anillo[i]
    const [lonj, latj] = anillo[j]
    const cruza = (lati > lat) !== (latj > lat) &&
      lon < ((lonj - loni) * (lat - lati)) / (latj - lati) + loni
    if (cruza) dentro = !dentro
  }
  return dentro
}

export function puntoEnGeometria(punto, geometry) {
  if (!punto || !geometry) return false
  return anillosDe(geometry).some((anillo) => puntoEnAnillo(punto, anillo))
}

// Para cada feature de `zonasBase`, busca la feature de `zonasComparar` cuyo
// polígono contiene el centroide de la primera. Devuelve un array ordenado de
// mayor a menor área con { zona, match, deltaNdvi } — match es null si el
// centroide no cayó en ninguna zona del otro vuelo (zona nueva o sin dato
// previo en esa posición).
export function emparejarZonas(zonasBase = [], zonasComparar = []) {
  const pares = zonasBase.map((zona) => {
    const centroide = centroideDe(zona.geometry)
    const match = centroide
      ? zonasComparar.find((otra) => puntoEnGeometria(centroide, otra.geometry)) || null
      : null
    const ndviBase = zona.properties?.ndvi_promedio
    const ndviMatch = match?.properties?.ndvi_promedio
    const deltaNdvi = match && ndviBase != null && ndviMatch != null
      ? ndviMatch - ndviBase
      : null
    return { zona, match, deltaNdvi }
  })

  return pares.sort((a, b) => (b.zona.properties?.area_ha || 0) - (a.zona.properties?.area_ha || 0))
}

// Proyección lineal lon/lat -> x/y de un viewBox SVG (equirrectangular,
// suficiente a la escala de un lote — no vale para comparar distancias).
export function crearProyector(bbox, ancho, alto, margen = 4) {
  const anchoLon = bbox.maxLon - bbox.minLon || 1
  const altoLat = bbox.maxLat - bbox.minLat || 1
  const escala = Math.min((ancho - margen * 2) / anchoLon, (alto - margen * 2) / altoLat)
  const offsetX = (ancho - anchoLon * escala) / 2
  const offsetY = (alto - altoLat * escala) / 2
  return ([lon, lat]) => [
    offsetX + (lon - bbox.minLon) * escala,
    offsetY + (bbox.maxLat - lat) * escala, // y invertido: SVG crece hacia abajo
  ]
}

export function pathSvgDeGeometria(geometry, proyectar) {
  return anillosDe(geometry)
    .map((anillo) => {
      const puntos = anillo.map((p) => proyectar(p).join(','))
      return `M${puntos.join('L')}Z`
    })
    .join(' ')
}
