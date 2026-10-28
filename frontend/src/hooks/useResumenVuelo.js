import { useEffect, useMemo, useState } from 'react'
import { obtenerDiagnostico } from '../api/analisis'
import { descargarReportePdf, descargarOrdenTrabajoPdf, exportarZonas } from '../api/reportes'
import { descargarBlob, extraerMensajeErrorBlob } from '../utils/descargarArchivo'

const SEVERIDAD_ORDEN = ['critica', 'moderada', 'leve', 'normal', 'vigorosa']

// Estadios tempranos (soja V1-V3 u homólogos) con cobertura de suelo todavía
// baja — el SAVI compensa el suelo expuesto mejor que el NDVI (ver reglas de
// índices por estadio en CLAUDE.md). El motor de diagnóstico en sí solo
// calcula sobre NDVI (ver nota en app/reportes/router.py), así que esto es
// una recomendación informativa, no un cambio del índice graficado.
const ESTADIOS_TEMPRANOS = new Set(['ve', 'vc', 'v1', 'v2', 'v3'])

function indiceRecomendado(estadioFenologico, ndviPromedioLote) {
  const estadio = (estadioFenologico || '').trim().toLowerCase()
  if (ESTADIOS_TEMPRANOS.has(estadio)) {
    return { indice: 'SAVI', motivo: `estadio ${estadioFenologico} — cobertura de suelo todavía baja` }
  }
  if (ndviPromedioLote != null && ndviPromedioLote > 0.75) {
    return { indice: 'GNDVI', motivo: 'NDVI > 0.75 — posible saturación en floración/llenado' }
  }
  return { indice: 'NDVI', motivo: estadio ? `estadio ${estadioFenologico}` : 'crecimiento vegetativo' }
}

function calcularStats(diagnostico) {
  if (!diagnostico) return null
  const features = diagnostico.features || []
  const metadata = diagnostico.metadata || {}

  const valoresNdvi = features
    .map(f => f.properties?.ndvi_promedio)
    .filter(v => typeof v === 'number')

  const porSeveridad = SEVERIDAD_ORDEN.reduce((acc, sev) => {
    acc[sev] = { area_ha: 0, zonas: 0 }
    return acc
  }, {})
  let areaTotal = 0
  for (const f of features) {
    const sev = f.properties?.severidad || 'normal'
    const area = f.properties?.area_ha || 0
    if (!porSeveridad[sev]) porSeveridad[sev] = { area_ha: 0, zonas: 0 }
    porSeveridad[sev].area_ha += area
    porSeveridad[sev].zonas += 1
    areaTotal += area
  }

  return {
    ndviPromedio: metadata.ndvi_promedio_lote ?? null,
    ndviMin: valoresNdvi.length > 0 ? Math.min(...valoresNdvi) : null,
    ndviMax: valoresNdvi.length > 0 ? Math.max(...valoresNdvi) : null,
    indicesDisponibles: metadata.indices_disponibles || [],
    recomendado: indiceRecomendado(metadata.estadio_fenologico, metadata.ndvi_promedio_lote),
    severidad: SEVERIDAD_ORDEN
      .map(sev => ({
        severidad: sev,
        area_ha: porSeveridad[sev].area_ha,
        zonas: porSeveridad[sev].zonas,
        pct: areaTotal > 0 ? (porSeveridad[sev].area_ha / areaTotal) * 100 : 0,
      }))
      .filter(s => s.zonas > 0),
    hayUnidadesManejo: (diagnostico.unidades_manejo || []).length > 0,
    hayZonas: features.length > 0,
  }
}

// Carga el diagnóstico de un vuelo al montarse — el padre (VuelosCalendario)
// solo monta este hook/componente cuando el usuario expande ese vuelo en el
// historial, así que esto ya es "on-demand": no se pide para todos los
// vuelos a la vez (generar_diagnostico() no es gratis).
export default function useResumenVuelo(loteId, vueloId) {
  const [diagnostico, setDiagnostico] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [descargando, setDescargando] = useState(null) // 'informe' | 'orden' | 'prescripcion' | null
  const [descargaError, setDescargaError] = useState('')

  useEffect(() => {
    if (!loteId || !vueloId) return
    setLoading(true)
    setError('')
    obtenerDiagnostico(loteId, vueloId)
      .then(setDiagnostico)
      .catch(() => setError('No se pudo generar el resumen de este vuelo.'))
      .finally(() => setLoading(false))
  }, [loteId, vueloId])

  const stats = useMemo(() => calcularStats(diagnostico), [diagnostico])

  function descargarInforme() {
    setDescargando('informe')
    setDescargaError('')
    descargarReportePdf(loteId, vueloId)
      .then(blob => descargarBlob(blob, `informe_ejecutivo_${vueloId}.pdf`))
      .catch(async (err) => setDescargaError(await extraerMensajeErrorBlob(err, 'No se pudo descargar el informe PDF.')))
      .finally(() => setDescargando(null))
  }

  function descargarOrden() {
    setDescargando('orden')
    setDescargaError('')
    descargarOrdenTrabajoPdf(loteId, vueloId)
      .then(blob => descargarBlob(blob, `orden_trabajo_${vueloId}.pdf`))
      .catch(async (err) => setDescargaError(await extraerMensajeErrorBlob(err, 'No se pudo descargar la orden de trabajo.')))
      .finally(() => setDescargando(null))
  }

  // A diferencia de los PDF, el export de zonas devuelve una URL firmada de
  // MinIO — no hay blob que armar, el navegador la abre directo (ver
  // comentario en api/reportes.js).
  function descargarPrescripcion() {
    setDescargando('prescripcion')
    setDescargaError('')
    exportarZonas(loteId, vueloId, 'shapefile')
      .then(({ url }) => window.open(url, '_blank'))
      .catch(async (err) => setDescargaError(await extraerMensajeErrorBlob(err, 'No se pudo generar la prescripción (SHP).')))
      .finally(() => setDescargando(null))
  }

  return {
    diagnostico, stats, loading, error,
    descargando, descargaError,
    descargarInforme, descargarOrden, descargarPrescripcion,
  }
}
