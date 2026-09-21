export const CULTIVOS = [
  { value: 'soja', label: 'Soja' },
  { value: 'maiz', label: 'Maíz' },
  { value: 'algodon', label: 'Algodón' },
  { value: 'sorgo', label: 'Sorgo' },
]

export const CULTIVO_LABEL = Object.fromEntries(CULTIVOS.map((c) => [c.value, c.label]))

export function etiquetaTipoCultivo(tipo) {
  return CULTIVO_LABEL[tipo] ?? tipo ?? ''
}

// GET /lotes devuelve los cultivos del lote del más reciente al más antiguo.
export function cultivoMasReciente(lote) {
  return lote?.cultivos?.[0] ?? null
}

function fmtFechaCorta(iso) {
  if (!iso) return null
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' })
}

// "Soja · DM 46i17 · siembra 15/11/2026"
export function descripcionCultivo(cultivo) {
  if (!cultivo) return ''
  const partes = [etiquetaTipoCultivo(cultivo.tipo_cultivo)]
  if (cultivo.variedad) partes.push(cultivo.variedad)
  const siembra = fmtFechaCorta(cultivo.fecha_siembra)
  if (siembra) partes.push(`siembra ${siembra}`)
  return partes.join(' · ')
}
