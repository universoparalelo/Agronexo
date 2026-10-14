import { useLocation, useNavigate } from 'react-router-dom'

const IconDashboard = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
    <rect x="3" y="3" width="7" height="7" rx="1.5"/>
    <rect x="14" y="3" width="7" height="7" rx="1.5"/>
    <rect x="3" y="14" width="7" height="7" rx="1.5"/>
    <rect x="14" y="14" width="7" height="7" rx="1.5"/>
  </svg>
)
const IconLotes = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
    <line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
  </svg>
)
const IconDiagnostico = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
  </svg>
)
const IconInformes = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
    <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
  </svg>
)
const IconConfig = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
  </svg>
)

export default function SidebarNav({ user, onVerDiagnosticos }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  const activeId = /^\/lotes\/[^/]+\/vuelos\//.test(pathname) ? 'diagnostico'
    : pathname.startsWith('/lotes') ? 'lotes'
    : pathname.startsWith('/dashboard') ? 'dashboard'
    : pathname.startsWith('/perfil') ? 'perfil'
    : null

  const sections = [
    {
      label: 'PRINCIPAL',
      items: [
        { id: 'dashboard', icon: <IconDashboard />, label: 'Dashboard', onClick: () => navigate('/dashboard') },
        { id: 'lotes',     icon: <IconLotes />,     label: 'Lotes',     onClick: () => navigate('/lotes') },
      ],
    },
    {
      label: 'RESULTADOS',
      items: [
        { id: 'diagnostico', icon: <IconDiagnostico />, label: 'Diagnósticos', onClick: () => onVerDiagnosticos?.() },
        { id: 'informes',    icon: <IconInformes />,    label: 'Informes',     proximamente: true },
      ],
    },
    {
      label: 'SISTEMA',
      items: [
        { id: 'perfil', icon: <IconConfig />, label: 'Mi perfil', onClick: () => navigate('/perfil') },
      ],
    },
  ]

  const initials = user?.nombre
    ? user.nombre.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'U'

  return (
    <aside className="sidebar-nav">
      <div className="sidebar-logo-wrap">
        <img src="/logo.png" alt="AgroNexo" className="sidebar-logo-img" />
        <span className="sidebar-beta">BETA</span>
      </div>

      <nav className="sidebar-menu">
        {sections.map(({ label, items }) => (
          <div key={label} className="sidebar-section">
            <span className="sidebar-section-label">{label}</span>
            {items.map(({ id, icon, label: itemLabel, onClick, proximamente }) => (
              <button
                key={id}
                className={`sidebar-link${activeId === id ? ' sidebar-link--active' : ''}${proximamente ? ' sidebar-link--disabled' : ''}`}
                onClick={proximamente ? undefined : onClick}
                disabled={proximamente}
                title={proximamente ? `${itemLabel} — Próximamente` : itemLabel}
              >
                <span className="sidebar-link-icon">{icon}</span>
                <span className="sidebar-link-label">{itemLabel}</span>
                {proximamente && <span className="sidebar-tag-proximamente">Próximamente</span>}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <button type="button" className="sidebar-user sidebar-user--clickable" onClick={() => navigate('/perfil')}>
        {user?.avatar_url
          ? <img src={user.avatar_url} alt="" className="sidebar-user-avatar sidebar-user-avatar--img" />
          : <div className="sidebar-user-avatar">{initials}</div>}
        <div className="sidebar-user-info">
          <span className="sidebar-user-name">{user?.nombre ?? 'Usuario'}</span>
          <span className="sidebar-user-role">{user?.nombre_empresa || 'Productor Agri'}</span>
        </div>
      </button>
    </aside>
  )
}
