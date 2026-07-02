import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import DetalleLote from './pages/DetalleLote'
import ResultadosVuelo from './pages/ResultadosVuelo'
import PrivateRoute from './components/PrivateRoute'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
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
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
