import { useEffect, useState } from 'react'
import { obtenerDiagnostico, obtenerZonas, recalcularDiagnostico } from '../api/analisis'
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
  const [recalculando, setRecalculando] = useState(false)
  const [generandoOrden, setGenerandoOrden] = useState(false)
  const [previewPdf, setPreviewPdf] = useState(null) // { titulo, blob, filename } | null

  useEffect(() => {
    if (!loteId || !vueloId) return
    setLoading(true)
    setError('')
    setZonas(null)
    setDiagnostico(null)
    setDiagnosticoError('')
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

  function handleRecalcular() {
    setRecalculando(true)
    setDiagnosticoError('')
    recalcularDiagnostico(loteId, vueloId)
      .then(setDiagnostico)
      .catch(() => setDiagnosticoError('No se pudo recalcular el diagnóstico.'))
      .finally(() => setRecalculando(false))
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
    recalculando, generandoOrden,
    previewPdf, cerrarPreviewPdf: () => setPreviewPdf(null),
    handleRecalcular, handleGenerarOrdenTrabajo,
  }
}
