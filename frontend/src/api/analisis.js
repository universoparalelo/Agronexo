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

// Busca escenas Sentinel-2 (Earth Search, sin auth) cerca de la fecha
// elegida por el usuario — devuelve la nubosidad de cada una para que el
// usuario elija otra fecha si la más cercana está nublada.
export const buscarImagenesSatelitales = (loteId, fecha, ventanaDias = 15) =>
  client.get(`/lotes/${loteId}/vuelos/imagenes-satelitales`, {
    params: { fecha, ventana_dias: ventanaDias },
  }).then(r => r.data)

// `cultivo` es { cultivo_id } para un cultivo ya cargado en el lote, o
// { cultivo: { tipo_cultivo, variedad, fecha_siembra, fecha_cosecha } } para crear uno nuevo.
export const crearVueloDesdeSatelite = (loteId, escenaId, fechaVuelo, estadioFenologico, indices = [], cultivo = {}) =>
  client.post(`/lotes/${loteId}/vuelos/desde-satelite`, {
    escena_id: escenaId,
    fecha_vuelo: fechaVuelo,
    estadio_fenologico: estadioFenologico || null,
    indices,
    ...cultivo,
  }).then(r => r.data)

// { soja: ['VE', 'VC', 'V1', ...], maiz: [...], algodon: [...], sorgo: [...] }
export const listarEstadiosFenologicos = () =>
  client.get('/estadios-fenologicos').then(r => r.data.estadios)

// Curva placeholder (migración 0025) de NDVI esperado por estadio
// para un cultivo — { cultivo, puntos: [{ estadio, orden, ndvi_esperado, ndvi_min, ndvi_max }] }
export const obtenerNdviEsperado = (cultivo) =>
  client.get('/estadios-fenologicos/ndvi-esperado', { params: { cultivo } }).then(r => r.data)

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

// Criterio técnico del agrónomo sobre una zona (RFDR-04).
// revision = { decision: 'aceptado'|'modificado'|'rechazado', causa_confirmada?, comentario? }
export const revisarZonaDiagnostico = (loteId, vueloId, zonaId, revision) =>
  client.put(`/lotes/${loteId}/vuelos/${vueloId}/diagnostico/zonas/${zonaId}/revision`, revision).then(r => r.data)

export const borrarRevisionZona = (loteId, vueloId, zonaId) =>
  client.delete(`/lotes/${loteId}/vuelos/${vueloId}/diagnostico/zonas/${zonaId}/revision`)

// { fecha_vuelo?, estadio_fenologico?, cultivo_id? } — devuelve diagnostico_desactualizado en true si cambió
// el cultivo o el estadio; el diagnóstico guardado se recalcula solo al abrirlo (firma de datos).
export const actualizarVuelo = (loteId, vueloId, datos) =>
  client.put(`/lotes/${loteId}/vuelos/${vueloId}`, datos).then(r => r.data)
