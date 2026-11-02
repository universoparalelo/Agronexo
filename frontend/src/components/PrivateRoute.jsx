import { Navigate } from 'react-router-dom'

function bienvenidaPendiente() {
  try {
    return JSON.parse(localStorage.getItem('usuario'))?.bienvenida_pendiente === true
  } catch {
    return false
  }
}

export default function PrivateRoute({ children, esBienvenida = false }) {
  if (!localStorage.getItem('access_token')) return <Navigate to="/login" replace />
  const pendiente = bienvenidaPendiente()
  if (pendiente && !esBienvenida) return <Navigate to="/bienvenida" replace />
  if (!pendiente && esBienvenida) return <Navigate to="/dashboard" replace />
  return children
}
