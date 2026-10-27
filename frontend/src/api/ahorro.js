import client from './client'

export const obtenerAhorroComparativo = (loteId, cultivoA, cultivoB) =>
  client.get(`/lotes/${loteId}/ahorro-comparativo`, {
    params: cultivoB ? { cultivo_a: cultivoA, cultivo_b: cultivoB } : { cultivo_a: cultivoA },
  }).then(r => r.data)

export const cargarPrecioProducto = (productoId, data) =>
  client.post(`/productos-fitosanitarios/${productoId}/precios`, data).then(r => r.data)

export const obtenerAhorroVuelo = (loteId, vueloId) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/ahorro`).then(r => r.data)
