import { Link } from 'react-router-dom'

const propsIcono = {
  width: 14,
  height: 14,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2.5,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
}

export function FlechaAtras() {
  return (
    <svg {...propsIcono}>
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  )
}

export function FlechaAdelante() {
  return (
    <svg {...propsIcono}>
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  )
}

// claro: para fondos claros (páginas de error); por defecto es el de las barras oscuras.
export default function BotonVolver({ to, onClick, claro = false, children }) {
  const clase = `btn-volver${claro ? ' btn-volver--claro' : ''}`
  const contenido = (
    <>
      <FlechaAtras />
      {children}
    </>
  )
  return to
    ? <Link to={to} className={clase}>{contenido}</Link>
    : <button type="button" className={clase} onClick={onClick}>{contenido}</button>
}
