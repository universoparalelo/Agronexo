import client from './client'

export const listarVuelos = (loteId) =>
  client.get(`/lotes/${loteId}/vuelos`).then(r => r.data)

export const obtenerEstadoVuelo = (loteId, vueloId) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/estado`).then(r => r.data)

export const obtenerZonas = (loteId, vueloId) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/zonas`).then(r => r.data)
