import { useAuth } from '../hooks/useAuth'
import SidebarNav from './SidebarNav'
import TopbarPanel from './TopbarPanel'

// Estructura común del panel: barra lateral + barra superior con ruta clicable.
// alto: pantallas de altura fija (mapa a pantalla completa) donde el contenido maneja su propio scroll.
export default function PanelLayout({ migas, onVerDiagnosticos, alto = false, children }) {
  const { user } = useAuth()

  return (
    <div className={`dashboard panel-shell${alto ? ' panel-shell--alto' : ''}`}>
      <SidebarNav user={user} onVerDiagnosticos={onVerDiagnosticos} plegable />
      <div className="dashboard-body">
        <TopbarPanel migas={migas} />
        {children}
      </div>
    </div>
  )
}
