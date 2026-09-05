import client from './client'

export const listarVuelos = (loteId) =>
  client.get(`/lotes/${loteId}/vuelos`).then(r => r.data)

export const obtenerEstadoVuelo = (loteId, vueloId) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/estado`).then(r => r.data)

export const obtenerZonas = (loteId, vueloId) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/resultado`).then(r => r.data)

export const eliminarVuelo = (loteId, vueloId) =>
  client.delete(`/lotes/${loteId}/vuelos/${vueloId}`)

export const reintentarVuelo = (loteId, vueloId) =>
  client.post(`/lotes/${loteId}/vuelos/${vueloId}/reintentar`).then(r => r.data)

export const inspeccionarGeotiff = (archivo, sensor) => {
  const fd = new FormData()
  fd.append('archivo', archivo)
  fd.append('sensor', sensor)
  return client.post('/lotes/inspeccionar-geotiff', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export const listarIndicesVuelo = (loteId, vueloId) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/indices`).then(r => r.data)

export const analizarIndice = (loteId, vueloId, indice, metodoUmbral = 'fijo') =>
  client.post(`/lotes/${loteId}/vuelos/${vueloId}/indices`, { indice, metodo_umbral: metodoUmbral }).then(r => r.data)

// Calcula varios índices adicionales en una sola corrida del worker (descarga
// y lectura de bandas compartida) en lugar de un POST /indices por índice.
export const analizarIndicesBatch = (loteId, vueloId, indices, metodoUmbral = 'fijo') =>
  client.post(`/lotes/${loteId}/vuelos/${vueloId}/indices/batch`, { indices, metodo_umbral: metodoUmbral }).then(r => r.data)

export const obtenerEstadoIndice = (loteId, vueloId, indice) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/indices/${indice}/estado`).then(r => r.data)

export const obtenerResultadoIndice = (loteId, vueloId, indice) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/indices/${indice}/resultado`).then(r => r.data)

// Devuelve el diagnóstico guardado del vuelo; si es la primera vez que se
// pide, el backend lo calcula y lo guarda antes de responder.
export const obtenerDiagnostico = (loteId, vueloId) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/diagnostico`).then(r => r.data)

// Fuerza el recálculo y sobrescribe el diagnóstico guardado del vuelo.
export const recalcularDiagnostico = (loteId, vueloId) =>
  client.post(`/lotes/${loteId}/vuelos/${vueloId}/diagnostico/recalcular`).then(r => r.data)
