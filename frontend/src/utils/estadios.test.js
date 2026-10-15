import { describe, it, expect } from 'vitest'
import { normalizarEstadio, buscarPuntoPorEstadio } from './estadios'

describe('normalizarEstadio', () => {
  it('pasa a minúsculas, saca acentos y cambia espacios por guión bajo', () => {
    expect(normalizarEstadio('Botón floral')).toBe('boton_floral')
    expect(normalizarEstadio('R3')).toBe('r3')
    expect(normalizarEstadio('  VT  ')).toBe('vt')
  })

  it('devuelve null para texto vacío', () => {
    expect(normalizarEstadio(null)).toBeNull()
    expect(normalizarEstadio('')).toBeNull()
  })
})

describe('buscarPuntoPorEstadio', () => {
  const puntos = [
    { estadio: 'V6', orden: 6, ndvi_esperado: 0.5 },
    { estadio: 'Botón floral', orden: 9, ndvi_esperado: 0.7 },
  ]

  it('matchea sin importar mayúsculas/acentos', () => {
    expect(buscarPuntoPorEstadio(puntos, 'v6')).toBe(puntos[0])
    expect(buscarPuntoPorEstadio(puntos, 'boton floral')).toBe(puntos[1])
  })

  it('devuelve null si no hay estadio cargado o no matchea ninguno', () => {
    expect(buscarPuntoPorEstadio(puntos, null)).toBeNull()
    expect(buscarPuntoPorEstadio(puntos, 'R8')).toBeNull()
  })
})
