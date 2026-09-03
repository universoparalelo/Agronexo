import client from './client'

export const listarLotes = () =>
  client.get('/lotes').then(r => r.data)

export const eliminarLote = (loteId) =>
  client.delete(`/lotes/${loteId}`)

export const listarCultivosLote = (loteId) =>
  client.get(`/lotes/${loteId}/cultivos`).then(r => r.data)
