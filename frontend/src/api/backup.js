import client from './client'

export const exportarTodo = () =>
  client.post('/backup/exportar').then(r => r.data)

export const analizarImportacion = (archivo) => {
  const fd = new FormData()
  fd.append('archivo', archivo)
  return client.post('/backup/importar/analizar', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export const importarBackup = (importacionId, modo) =>
  client.post(`/backup/importar/${importacionId}`, { modo }).then(r => r.data)

export const cancelarImportacion = (importacionId) =>
  client.delete(`/backup/importar/${importacionId}`)
