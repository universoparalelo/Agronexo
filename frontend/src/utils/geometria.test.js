import { describe, it, expect } from 'vitest'
import { areaGeodesicaM2, tieneAutointerseccion, AREA_MIN_HA, AREA_MAX_HA } from './geometria'

function anillo(coordsLngLat) {
  return coordsLngLat.map(([lng, lat]) => ({ lng, lat }))
}

// Mismo rectángulo que _GEOM en tests/test_lotes.py (backend) — ~27 ha.
const RECTANGULO = [
  [-60.6753, -27.4693],
  [-60.6701, -27.4693],
  [-60.6701, -27.4741],
  [-60.6753, -27.4741],
  [-60.6753, -27.4693],
]

// "Bowtie" — las aristas A-B y C-D cruzan por el centro del rectángulo.
const BOWTIE = [
  [-60.70, -27.45],
  [-60.65, -27.50],
  [-60.70, -27.50],
  [-60.65, -27.45],
  [-60.70, -27.45],
]

describe('areaGeodesicaM2', () => {
  it('calcula un área cercana a la aproximación plana para un rectángulo chico', () => {
    const areaHa = areaGeodesicaM2(anillo(RECTANGULO)) / 10000

    const lat = -27.47
    const metrosPorGradoLng = 111320 * Math.cos((lat * Math.PI) / 180)
    const metrosPorGradoLat = 110540
    const anchoM = Math.abs(-60.6701 - -60.6753) * metrosPorGradoLng
    const altoM = Math.abs(-27.4741 - -27.4693) * metrosPorGradoLat
    const areaAproxHa = (anchoM * altoM) / 10000

    expect(areaHa).toBeGreaterThan(AREA_MIN_HA)
    expect(areaHa).toBeLessThan(AREA_MAX_HA)
    expect(Math.abs(areaHa - areaAproxHa) / areaAproxHa).toBeLessThan(0.05)
  })

  it('da un área ~0 para un polígono degenerado (todos los vértices iguales)', () => {
    const coords = [[-60, -27], [-60, -27], [-60, -27], [-60, -27]]
    expect(areaGeodesicaM2(anillo(coords))).toBeCloseTo(0, 5)
  })
})

describe('tieneAutointerseccion', () => {
  it('no detecta autointersección en un rectángulo simple', () => {
    expect(tieneAutointerseccion(RECTANGULO)).toBe(false)
  })

  it('detecta autointersección en un polígono "moño" (bowtie)', () => {
    expect(tieneAutointerseccion(BOWTIE)).toBe(true)
  })

  it('ignora aristas adyacentes que comparten vértice (no es un falso positivo)', () => {
    // Triángulo — el mínimo de vértices donde toda arista es adyacente a las demás.
    const triangulo = [
      [-60.70, -27.45],
      [-60.66, -27.45],
      [-60.68, -27.49],
      [-60.70, -27.45],
    ]
    expect(tieneAutointerseccion(triangulo)).toBe(false)
  })
})
