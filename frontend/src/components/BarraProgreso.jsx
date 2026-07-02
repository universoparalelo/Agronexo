export default function BarraProgreso({ progreso, mensaje, estado }) {
  const pct = progreso ?? 0

  return (
    <div className="barra-progreso-wrap">
      <div className="barra-progreso-header">
        <span className="barra-estado-label">
          {estado === 'pendiente' ? 'En cola de procesamiento...' : 'Procesando imagen...'}
        </span>
        <span className="barra-pct">{pct}%</span>
      </div>
      <div className="barra-track">
        <div className="barra-fill" style={{ width: `${pct}%` }} />
      </div>
      {mensaje && <p className="barra-mensaje">{mensaje}</p>}
    </div>
  )
}
