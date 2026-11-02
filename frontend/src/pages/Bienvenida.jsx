import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { completarBienvenida } from '../api/perfil'
import { useAuth } from '../hooks/useAuth'

export default function Bienvenida() {
  const [nombre, setNombre] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)
  const { actualizarUsuario } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setGuardando(true)
    try {
      actualizarUsuario(await completarBienvenida({ nombre, email }))
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'No se pudo guardar. Revisá los datos.')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="l2-root l2-loaded">
      <div className="l2-bg" />
      <div className="l2-modal">
        <div className="l2-modal-header">
          <img src="/logo.png" alt="AgroNexo" className="l2-logo" />
          <h2>Te damos la bienvenida</h2>
          <p>Contanos quién sos. Estos datos aparecen en tus reportes y órdenes de trabajo, y se guardan solo en esta computadora.</p>
        </div>

        <form onSubmit={handleSubmit} className="l2-form">
          <div className="l2-field">
            <label htmlFor="bienvenida-nombre">Nombre</label>
            <div className="l2-input-wrap">
              <input
                id="bienvenida-nombre"
                type="text"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Nombre y apellido"
                maxLength={200}
                required
                autoFocus
              />
            </div>
          </div>

          <div className="l2-field">
            <label htmlFor="bienvenida-email">Correo</label>
            <div className="l2-input-wrap">
              <input
                id="bienvenida-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nombre@empresa.com"
                maxLength={255}
                required
              />
            </div>
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="l2-btn-submit" disabled={guardando}>
            {guardando ? 'Guardando...' : 'Empezar'}
          </button>
        </form>
      </div>
    </div>
  )
}
