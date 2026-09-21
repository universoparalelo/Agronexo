import { Fragment } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

function fechaHoy() {
  return new Date().toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

// migas: [{ label, to? }] — la última es la pantalla actual y no lleva enlace.
export default function TopbarPanel({ migas }) {
  const navigate = useNavigate()
  const { logout } = useAuth()

  return (
    <header className="topbar">
      <nav className="topbar-breadcrumb" aria-label="Ruta">
        {migas.map((m, i) => {
          const ultima = i === migas.length - 1
          return (
            <Fragment key={`${i}-${m.label}`}>
              {i > 0 && <span className="breadcrumb-sep">›</span>}
              {ultima || !m.to
                ? <span className={ultima ? 'breadcrumb-active' : undefined}>{m.label}</span>
                : <Link to={m.to} className="breadcrumb-link">{m.label}</Link>}
            </Fragment>
          )
        })}
      </nav>
      <div className="topbar-actions">
        <div className="topbar-date">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          <span>{fechaHoy()}</span>
        </div>
        <button className="btn-salir" onClick={() => { logout(); navigate('/login') }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
            <polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          Salir
        </button>
      </div>
    </header>
  )
}
