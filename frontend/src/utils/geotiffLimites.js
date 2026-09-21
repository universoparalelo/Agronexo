import { fromBlob } from 'geotiff'
import proj4 from 'proj4'

// Tolerancia para considerar que el GeoTIFF "está cerca" del lote: los
// ortomosaicos casi nunca coinciden exacto con el límite dibujado a mano, así
// que solo se rechaza cuando queda claramente lejos.
const TOLERANCIA_M = 1000

function definicionEpsg(codigo) {
  if (codigo === 3857) return 'EPSG:3857'
  if (codigo >= 32601 && codigo <= 32660) return `+proj=utm +zone=${codigo - 32600} +datum=WGS84 +units=m +no_defs`
  if (codigo >= 32701 && codigo <= 32760) return `+proj=utm +zone=${codigo - 32700} +south +datum=WGS84 +units=m +no_defs`
  // POSGAR 2007 (5343–5349) y POSGAR 94 (22181–22187): Gauss-Krüger fajas 1–7 de Argentina.
  const faja = codigo >= 5343 && codigo <= 5349 ? codigo - 5342
    : codigo >= 22181 && codigo <= 22187 ? codigo - 22180
    : null
  if (faja) {
    return `+proj=tmerc +lat_0=-90 +lon_0=${-72 + 3 * (faja - 1)} +k=1 +x_0=${faja * 1000000 + 500000} +y_0=0 +ellps=GRS80 +units=m +no_defs`
  }
  return null
}

// Devuelve el polígono GeoJSON (lng/lat) que cubre el GeoTIFF, o null si no se
// puede determinar (CRS desconocido, sin georreferencia, archivo raro). Es
// informativo: si devuelve null el flujo de carga sigue sin validar ubicación.
export async function leerLimitesGeotiff(archivo) {
  try {
    const tiff = await fromBlob(archivo)
    const imagen = await tiff.getImage()
    const [minX, minY, maxX, maxY] = imagen.getBoundingBox()
    const claves = imagen.getGeoKeys() ?? {}

    let convertir
    if (claves.ProjectedCSTypeGeoKey && claves.ProjectedCSTypeGeoKey !== 32767) {
      const def = definicionEpsg(claves.ProjectedCSTypeGeoKey)
      if (!def) return null
      convertir = (p) => proj4(def, 'EPSG:4326', p)
    } else if (claves.GeographicTypeGeoKey) {
      convertir = (p) => p
    } else {
      return null
    }

    const anillo = [[minX, minY], [maxX, minY], [maxX, maxY], [minX, maxY], [minX, minY]].map(convertir)
    if (anillo.some(([lng, lat]) => !Number.isFinite(lng) || !Number.isFinite(lat))) return null
    return { type: 'Polygon', coordinates: [anillo] }
  } catch {
    return null
  }
}

function bbox(poligono) {
  const anillo = poligono.coordinates[0]
  const lngs = anillo.map((c) => c[0])
  const lats = anillo.map((c) => c[1])
  return { minLng: Math.min(...lngs), maxLng: Math.max(...lngs), minLat: Math.min(...lats), maxLat: Math.max(...lats) }
}

// Comparación por bounding box con margen: alcanza para detectar un archivo
// de otro campo/provincia sin fallar por diferencias chicas de borde.
export function geotiffCercaDelLote(geotiff, lote) {
  const g = bbox(geotiff)
  const l = bbox(lote)
  const latMedia = (l.minLat + l.maxLat) / 2
  const margenLat = TOLERANCIA_M / 111320
  const margenLng = margenLat / Math.max(Math.cos((latMedia * Math.PI) / 180), 0.01)
  return (
    g.minLng <= l.maxLng + margenLng && g.maxLng >= l.minLng - margenLng &&
    g.minLat <= l.maxLat + margenLat && g.maxLat >= l.minLat - margenLat
  )
}
