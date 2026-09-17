import client from './client'

export const descargarReportePdf = (loteId, vueloId) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/reporte/pdf`, { responseType: 'blob' }).then(r => r.data)

export const descargarOrdenTrabajoPdf = (loteId, vueloId) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/orden-trabajo/pdf`, { responseType: 'blob' }).then(r => r.data)

// A diferencia de los PDF, esto no descarga el archivo — devuelve una URL
// firmada de MinIO ({url, expira_en_segundos, ...}) que el frontend abre
// directo, sin pasar por el cliente axios (la firma ya autentica).
export const exportarZonas = (loteId, vueloId, formato) =>
  client.get(`/lotes/${loteId}/vuelos/${vueloId}/zonas/export`, { params: { formato } }).then(r => r.data)
