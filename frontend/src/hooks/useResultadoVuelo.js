import { useEffect, useState } from 'react'
import { obtenerDiagnostico, obtenerZonas } from '../api/analisis'
import { obtenerAhorroVuelo } from '../api/ahorro'
import { descargarOrdenTrabajoPdf } from '../api/reportes'
import { extraerMensajeErrorBlob } from '../utils/descargarArchivo'

// Carga zonas + diagnóstico de UN vuelo y expone las acciones sobre él
// (recalcular, generar orden de trabajo). Se usa una vez por panel visible —
// el modo comparación abre dos paneles, cada uno con su propia instancia de
// este hook, para no mezclar el estado de carga de un vuelo con el del otro.
export default function useResultadoVuelo(loteId, vueloId, nombreLote) {
  const [zonas, setZonas] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [tab, setTab] = useState('zonas')
  const [diagnostico, setDiagnostico] = useState(null)
  const [diagnosticoLoading, setDiagnosticoLoading] = useState(false)
  const [diagnosticoError, setDiagnosticoError] = useState('')
  const [ahorro, setAhorro] = useState(null)
  const [ahorroLoading, setAhorroLoading] = useState(false)
  const [ahorroError, setAhorroError] = useState('')
  const [generandoOrden, setGenerandoOrden] = useState(false)
  const [previewPdf, setPreviewPdf] = useState(null) // { titulo, blob, filename } | null

  useEffect(() => {
    if (!loteId || !vueloId) return
    setLoading(true)
    setError('')
    setZonas(null)
    setDiagnostico(null)
    setDiagnosticoError('')
    setAhorro(null)
    setAhorroError('')
    obtenerZonas(loteId, vueloId)
      .then(setZonas)
      .catch(() => setError('No se pudieron cargar los resultados del análisis.'))
      .finally(() => setLoading(false))
  }, [loteId, vueloId])

  useEffect(() => {
    if (!loteId || !vueloId || tab !== 'diagnostico' || diagnostico || diagnosticoLoading) return
    setDiagnosticoLoading(true)
    setDiagnosticoError('')
    obtenerDiagnostico(loteId, vueloId)
      .then(setDiagnostico)
      .catch(() => setDiagnosticoError('No se pudo generar el diagnóstico para este análisis.'))
      .finally(() => setDiagnosticoLoading(false))
  }, [tab, loteId, vueloId, diagnostico, diagnosticoLoading])

  // El ahorro sale del diagnóstico: se pide al abrir la pestaña y se vuelve a pedir si se recalcula.
  useEffect(() => {
    if (!loteId || !vueloId || tab !== 'ahorro' || ahorro || ahorroLoading || ahorroError) return
    setAhorroLoading(true)
    obtenerAhorroVuelo(loteId, vueloId)
      .then(setAhorro)
      .catch((err) => setAhorroError(err.response?.data?.detail || 'No se pudo calcular el ahorro de este análisis.'))
      .finally(() => setAhorroLoading(false))
  }, [tab, loteId, vueloId, ahorro, ahorroLoading, ahorroError])

  function recargarAhorro() {
    setAhorro(null)
    setAhorroError('')
  }

  function handleGenerarOrdenTrabajo() {
    setGenerandoOrden(true)
    setDiagnosticoError('')
    descargarOrdenTrabajoPdf(loteId, vueloId)
      .then((blob) => setPreviewPdf({
        titulo: `Orden de trabajo — ${nombreLote ?? ''}`,
        blob,
        filename: `orden_trabajo_${vueloId}.pdf`,
      }))
      .catch(async (err) => setDiagnosticoError(await extraerMensajeErrorBlob(err, 'No se pudo generar la orden de trabajo.')))
      .finally(() => setGenerandoOrden(false))
  }

  return {
    zonas, loading, error,
    tab, setTab,
    diagnostico, diagnosticoLoading, diagnosticoError,
    ahorro, ahorroLoading, ahorroError, recargarAhorro,
    generandoOrden,
    previewPdf, cerrarPreviewPdf: () => setPreviewPdf(null),
    handleGenerarOrdenTrabajo,
  }
}
