export const ORDEN_CLASES = ['vigorosa', 'normal', 'deficiente', 'critica']

// Agrega las features de un GeoJSON de zonas en estadísticas por clase —
// misma agregación que usa TablaZonas, extraída para poder compararla entre
// dos vuelos (HU-R4-09).
export function calcularStatsZonas(features = []) {
  const porClase = ORDEN_CLASES.reduce((acc, clase) => {
    const zonas = features.filter(f => f.properties?.clase === clase)
    const area = zonas.reduce((s, f) => s + (f.properties?.area_ha || 0), 0)
    const ndviProm = zonas.length > 0
      ? zonas.reduce((s, f) => s + (f.properties?.ndvi_promedio || 0), 0) / zonas.length
      : null
    acc[clase] = { area, ndvi: ndviProm, poligonos: zonas.length }
    return acc
  }, {})

  const totalArea = Object.values(porClase).reduce((s, c) => s + c.area, 0)

  // Promedio general ponderado por área — no es el promedio de los 4
  // promedios por clase, que subestimaría clases con mucha superficie.
  const sumaPonderada = features.reduce((s, f) => {
    const area = f.properties?.area_ha || 0
    const ndvi = f.properties?.ndvi_promedio
    return ndvi != null ? s + area * ndvi : s
  }, 0)
  const areaConNdvi = features.reduce((s, f) => (
    f.properties?.ndvi_promedio != null ? s + (f.properties?.area_ha || 0) : s
  ), 0)
  const ndviPromedioGeneral = areaConNdvi > 0 ? sumaPonderada / areaConNdvi : null

  return { porClase, totalArea, totalPoligonos: features.length, ndviPromedioGeneral }
}
