import { describe, expect, it } from 'vitest'
import { parsearCoordenadas } from './coordenadas'

describe('parsearCoordenadas', () => {
  it('acepta decimales separados por coma, espacio o punto y coma', () => {
    expect(parsearCoordenadas('-27.45, -59.05')).toEqual({ lat: -27.45, lng: -59.05 })
    expect(parsearCoordenadas('-27.45 -59.05')).toEqual({ lat: -27.45, lng: -59.05 })
    expect(parsearCoordenadas('-27.45;-59.05')).toEqual({ lat: -27.45, lng: -59.05 })
  })

  it('acepta hemisferios y el símbolo de grados', () => {
    expect(parsearCoordenadas('27.45 S, 59.05 W')).toEqual({ lat: -27.45, lng: -59.05 })
    expect(parsearCoordenadas('27.45°S 59.05°O')).toEqual({ lat: -27.45, lng: -59.05 })
    expect(parsearCoordenadas('10N 20E')).toEqual({ lat: 10, lng: 20 })
  })

  it('acepta coma decimal cuando el separador es un espacio', () => {
    expect(parsearCoordenadas('-27,45 -59,05')).toEqual({ lat: -27.45, lng: -59.05 })
  })

  it('rechaza rangos imposibles y texto que no son coordenadas', () => {
    expect(parsearCoordenadas('95, 10')).toBeNull()
    expect(parsearCoordenadas('10, 200')).toBeNull()
    expect(parsearCoordenadas('Resistencia, Chaco')).toBeNull()
    expect(parsearCoordenadas('')).toBeNull()
    expect(parsearCoordenadas('-27.45')).toBeNull()
  })
})
