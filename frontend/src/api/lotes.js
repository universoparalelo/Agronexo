import client from './client'

export const listarLotes = (params = {}) =>
  client.get('/lotes', { params }).then(r => r.data)

export const eliminarLote = (loteId) =>
  client.delete(`/lotes/${loteId}`)
