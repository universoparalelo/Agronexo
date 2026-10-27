import client from './client'

export const cargarPrecioProducto = (productoId, data) =>
  client.post(`/productos-fitosanitarios/${productoId}/precios`, data).then(r => r.data)

export const obtenerAhorroVuelo = (loteId, vueloId) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/ahorro`).then(r => r.data)
