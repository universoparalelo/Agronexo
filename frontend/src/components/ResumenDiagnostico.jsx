const SIN_PROBLEMA = ['R99', 'R00']

const ha = n => n.toFixed(1).replace('.', ',')

export default function ResumenDiagnostico({ diagnostico }) {
  const features = diagnostico?.features
  if (!features?.length) return null

  const area = f => f.properties?.area_ha ?? 0
  const conProblema = features.filter(f => !SIN_PROBLEMA.includes(f.properties?.regla_id))
  const sinProblemas = features.filter(f => f.properties?.regla_id === 'R99')
  const areaTotal = features.reduce((suma, f) => suma + area(f), 0)
  const areaAfectada = conProblema.reduce((suma, f) => suma + area(f), 0)
  const plural = (n, uno, varios) => (n === 1 ? uno : varios)

  return (
    <p className="diagnostico-resumen diagnostico-resumen--corto">
      Total: {features.length} {plural(features.length, 'zona', 'zonas')} ({ha(areaTotal)} ha)
      {conProblema.length > 0 && (
        <> · <strong className="resumen-atencion">{conProblema.length} {plural(conProblema.length, 'requiere', 'requieren')} atención ({ha(areaAfectada)} ha)</strong></>
      )}
      {sinProblemas.length > 0 && <> · {sinProblemas.length} sin {plural(sinProblemas.length, 'problema', 'problemas')}</>}
    </p>
  )
}
