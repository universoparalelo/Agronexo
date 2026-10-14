import client from './client'

export const listarProductosFitosanitarios = () =>
  client.get('/productos-fitosanitarios').then(r => r.data)
