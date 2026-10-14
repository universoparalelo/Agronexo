import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LandingOriginal from './pages/LandingOriginal'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Lotes from './pages/Lotes'
import DetalleLote from './pages/DetalleLote'
import ResultadosVuelo from './pages/ResultadosVuelo'
import AhorroComparativo from './pages/AhorroComparativo'
import PerfilUsuario from './pages/PerfilUsuario'
import PrivateRoute from './components/PrivateRoute'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingOriginal />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/dashboard"
          element={
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          }
        />
        <Route
          path="/lotes"
          element={
            <PrivateRoute>
              <Lotes />
            </PrivateRoute>
          }
        />
        <Route
          path="/lotes/:loteId"
          element={
            <PrivateRoute>
              <DetalleLote />
            </PrivateRoute>
          }
        />
        <Route
          path="/lotes/:loteId/vuelos/:vueloId"
          element={
            <PrivateRoute>
              <ResultadosVuelo />
            </PrivateRoute>
          }
        />
        <Route
          path="/lotes/:loteId/ahorro"
          element={
            <PrivateRoute>
              <AhorroComparativo />
            </PrivateRoute>
          }
        />
        <Route
          path="/perfil"
          element={
            <PrivateRoute>
              <PerfilUsuario />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
