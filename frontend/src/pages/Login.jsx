import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const FEATURES = [
  {
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
      </svg>
    ),
    title: 'NDVI / NDRE',
    desc: 'Salud del cultivo en tiempo real',
  },
  {
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
    ),
    title: 'Detección anomalías',
    desc: 'Plagas, estrés hídrico y más',
  },
  {
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
        <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
      </svg>
    ),
    title: 'Planes fumigación',
    desc: 'Prescripciones dosis variable',
  },
  {
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
        <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
      </svg>
    ),
    title: 'Seguimiento en vivo',
    desc: 'Evolución constante del lote',
  },
]

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [remember, setRemember] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    const t = setTimeout(() => setIsLoaded(true), 50)
    return () => clearTimeout(t)
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(msg || 'Error al iniciar sesión. Verificá tus credenciales.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`l2-root${isLoaded ? ' l2-loaded' : ''}`}>
      {/* Fondo */}
      <div className="l2-bg" />

      {/* Logo */}
      <img src="/logo.png" alt="AgroNexo" className="l2-logo" />

      {/* Modal central */}
      <div className="l2-modal">
        <div className="l2-modal-header l2-stagger l2-stagger-1">
          <h2>Bienvenido</h2>
          <p>Ingresá tus credenciales para continuar.</p>
        </div>

        <form onSubmit={handleSubmit} className="l2-form">
          <div className="l2-field l2-stagger l2-stagger-2">
            <label htmlFor="l2-email">Email</label>
            <div className="l2-input-wrap">
              <span className="l2-icon">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                  <polyline points="22,6 12,13 2,6"/>
                </svg>
              </span>
              <input
                id="l2-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nombre@empresa.com"
                required
                autoFocus
              />
            </div>
          </div>

          <div className="l2-field l2-stagger l2-stagger-3">
            <label htmlFor="l2-password">Contraseña</label>
            <div className="l2-input-wrap">
              <span className="l2-icon">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0110 0v4"/>
                </svg>
              </span>
              <input
                id="l2-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                className="l2-icon-right"
                onClick={() => setShowPassword(v => !v)}
                tabIndex={-1}
              >
                {showPassword ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>
                    <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                ) : (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                )}
              </button>
            </div>
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="l2-options l2-stagger l2-stagger-4">
            <label className="l2-remember">
              <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
              <span>Recordarme</span>
            </label>
            <button type="button" className="l2-forgot">¿Olvidaste tu contraseña?</button>
          </div>

          <button type="submit" className="l2-btn-submit l2-stagger l2-stagger-5" disabled={loading}>
            {loading ? 'Ingresando...' : (
              <>
                Acceder
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="5" y1="12" x2="19" y2="12"/>
                  <polyline points="12 5 19 12 12 19"/>
                </svg>
              </>
            )}
          </button>
        </form>

        <p className="l2-register l2-stagger l2-stagger-6">
          ¿No tenés cuenta?{' '}
          <button type="button" className="l2-register-link">Registrarse</button>
        </p>
      </div>

      {/* Pie */}
      <div className="l2-footer">
        <button type="button">Privacidad</button>
        <span>·</span>
        <button type="button">Términos</button>
        <span>·</span>
        <span>© 2026 AgroNexo</span>
      </div>
    </div>
  )
}
