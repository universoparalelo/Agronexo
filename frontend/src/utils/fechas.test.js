import { describe, it, expect } from 'vitest'
import { fechaISOLocal, fechaVuelo } from './fechas'

describe('fechaVuelo', () => {
  it('conserva el día calendario de un vuelo guardado a medianoche UTC', () => {
    expect(fechaISOLocal(fechaVuelo('2026-08-06T00:00:00+00:00'))).toBe('2026-08-06')
  })
})
