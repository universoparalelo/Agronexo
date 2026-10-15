import { describe, it, expect } from 'vitest'
import { bboxDeGeometrias, centroideDe, puntoEnGeometria, emparejarZonas, crearProyector } from './cambioZonas'

const CUADRADO_IZQUIERDA = {
  type: 'Polygon',
  coordinates: [[[0, 0], [0, 10], [5, 10], [5, 0], [0, 0]]],
}
const CUADRADO_DERECHA = {
  type: 'Polygon',
  coordinates: [[[5, 0], [5, 10], [10, 10], [10, 0], [5, 0]]],
}
const CUADRADO_COMPLETO = {
  type: 'Polygon',
  coordinates: [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]],
}

describe('puntoEnGeometria', () => {
  it('detecta un punto adentro y uno afuera de un polígono', () => {
    expect(puntoEnGeometria([2, 5], CUADRADO_IZQUIERDA)).toBe(true)
    expect(puntoEnGeometria([8, 5], CUADRADO_IZQUIERDA)).toBe(false)
  })
})

describe('centroideDe', () => {
  it('promedia los vértices del anillo exterior (incluye el punto de cierre repetido)', () => {
    // anillo cerrado de 5 puntos (el primero se repite al final) -> promedio
    // de lat = (0+10+10+0+0)/5 = 4, no 5: no es el centroide geométrico real,
    // alcanza para decidir en qué zona del otro vuelo cae.
    const [lon, lat] = centroideDe(CUADRADO_IZQUIERDA)
    expect(lon).toBeCloseTo(2, 5)
    expect(lat).toBeCloseTo(4, 5)
  })
})

describe('bboxDeGeometrias', () => {
  it('calcula el bbox que cubre todas las geometrías dadas', () => {
    const bbox = bboxDeGeometrias([CUADRADO_IZQUIERDA, CUADRADO_DERECHA])
    expect(bbox).toEqual({ minLon: 0, minLat: 0, maxLon: 10, maxLat: 10 })
  })

  it('devuelve null sin geometrías', () => {
    expect(bboxDeGeometrias([])).toBeNull()
  })
})

describe('emparejarZonas', () => {
  const feat = (geometry, ndvi, area) => ({ geometry, properties: { ndvi_promedio: ndvi, area_ha: area } })

  it('empareja por posición y calcula el delta de NDVI (B - A)', () => {
    const zonasA = [feat(CUADRADO_IZQUIERDA, 0.5, 5)]
    const zonasB = [feat(CUADRADO_COMPLETO, 0.3, 10)]

    const [{ zona, match, deltaNdvi }] = emparejarZonas(zonasA, zonasB)
    expect(zona).toBe(zonasA[0])
    expect(match).toBe(zonasB[0])
    expect(deltaNdvi).toBeCloseTo(-0.2, 5)
  })

  it('no empareja si el centroide de la zona base no cae en ninguna del otro vuelo', () => {
    const zonasA = [feat(CUADRADO_DERECHA, 0.5, 5)]
    const zonasB = [feat(CUADRADO_IZQUIERDA, 0.3, 5)]

    const [{ match, deltaNdvi }] = emparejarZonas(zonasA, zonasB)
    expect(match).toBeNull()
    expect(deltaNdvi).toBeNull()
  })

  it('ordena de mayor a menor área', () => {
    const chica = feat(CUADRADO_IZQUIERDA, 0.5, 1)
    const grande = feat(CUADRADO_DERECHA, 0.5, 20)
    const pares = emparejarZonas([chica, grande], [])
    expect(pares[0].zona).toBe(grande)
    expect(pares[1].zona).toBe(chica)
  })
})

describe('crearProyector', () => {
  it('invierte el eje Y (lat mayor -> y menor) y respeta el bbox', () => {
    const bbox = { minLon: 0, minLat: 0, maxLon: 10, maxLat: 10 }
    const proyectar = crearProyector(bbox, 100, 100, 0)
    const [, yArriba] = proyectar([0, 10])
    const [, yAbajo] = proyectar([0, 0])
    expect(yArriba).toBeLessThan(yAbajo)
  })
})
