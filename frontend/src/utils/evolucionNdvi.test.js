import { describe, it, expect } from 'vitest'
import { explicarEvolucion, estadoVsEsperado, fechaVueloCorta } from './evolucionNdvi'

const esperado = (valor) => ({ valor, min: valor - 0.12, max: valor + 0.12 })

describe('estadoVsEsperado', () => {
  it('clasifica contra el rango normal', () => {
    expect(estadoVsEsperado({ ndviProm: 0.3, esperado: esperado(0.6) })).toBe('debajo')
    expect(estadoVsEsperado({ ndviProm: 0.6, esperado: esperado(0.6) })).toBe('normal')
    expect(estadoVsEsperado({ ndviProm: 0.9, esperado: esperado(0.6) })).toBe('encima')
    expect(estadoVsEsperado({ ndviProm: 0.9, esperado: null })).toBeNull()
  })
})

describe('fechaVueloCorta', () => {
  it('no corre la fecha un día en husos horarios negativos', () => {
    expect(fechaVueloCorta('2026-08-06T00:00:00+00:00')).toMatch(/^06/)
  })
})

describe('explicarEvolucion', () => {
  it('avisa si no hay vuelos comparables', () => {
    const [p] = explicarEvolucion([{ ndviProm: 0.5, esperado: null, causas: {} }])
    expect(p).toMatch(/No se puede comparar/)
  })

  it('explica la diferencia con las causas de los vuelos por debajo', () => {
    const parrafos = explicarEvolucion([
      { fecha: '2026-09-01T00:00:00Z', estadio: 'V4', ndviProm: 0.5, esperado: esperado(0.5), causas: {} },
      {
        fecha: '2026-10-01T00:00:00Z', estadio: 'R3', ndviProm: 0.45, esperado: esperado(0.75),
        causas: { estres_biotico_fungico: 3.2, estres_nutricional_nitrogeno: 1 },
      },
    ])
    expect(parrafos[0]).toBe('En 1 de 2 vuelos el lote estuvo dentro del rango normal para su etapa; en 1 quedó por debajo.')
    expect(parrafos[1]).toMatch(/0\.30 por debajo de lo esperado/)
    expect(parrafos[1]).toMatch(/agrandando/)
    expect(parrafos[2]).toMatch(/enfermedad fúngica probable \(3\.2 ha\), déficit de nitrógeno \(1\.0 ha\)/)
  })

  it('caída pareja sin causa puntual', () => {
    const parrafos = explicarEvolucion([
      { fecha: '2026-10-01T00:00:00Z', estadio: 'R3', ndviProm: 0.3, esperado: esperado(0.75), causas: {} },
    ])
    expect(parrafos[2]).toMatch(/pareja en todo el lote/)
  })
})
