import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Login2 from './pages/Login2'
import Dashboard from './pages/Dashboard'
import DetalleLote from './pages/DetalleLote'
import ResultadosVuelo from './pages/ResultadosVuelo'
import PrivateRoute from './components/PrivateRoute'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/login2" element={<Login2 />} />
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
