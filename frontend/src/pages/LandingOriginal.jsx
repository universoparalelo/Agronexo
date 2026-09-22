import './LandingOriginal.css'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

/* ── Data ── */
const DYNAMIC_WORDS = ['cultivos', 'lotes', 'datos', 'rendimiento', 'recursos']

const CAPACIDADES = [
  'Captura Multiespectral',
  'Análisis IA en tiempo real',
  'Diagnóstico de Anomalías',
  'Prescripción Diferenciada',
  'Índices NDVI · NDRE · SAVI',
  'Zonificación Automática',
  'Órdenes de Trabajo ISO-XML',
  'Georreferenciación RTK'
]

/* ── Component ── */
export default function LandingOriginal() {
  const navigate = useNavigate()
  const [isLoaded, setIsLoaded] = useState(false)
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [scrollY, setScrollY] = useState(0)
  const [typedWord, setTypedWord] = useState(DYNAMIC_WORDS[0])
  const [dashTilt, setDashTilt] = useState(0)

  const dashRef = useRef(null)
  const observerRef = useRef(null)

  // Typewriter word rotation
  useEffect(() => {
    let idx = 0
    let pos = DYNAMIC_WORDS[0].length
    let deleting = false
    let timer
    const tick = () => {
      const word = DYNAMIC_WORDS[idx]
      if (!deleting) {
        if (pos < word.length) {
          pos++
          setTypedWord(word.slice(0, pos))
          timer = setTimeout(tick, 90)
        } else {
          deleting = true
          timer = setTimeout(tick, 2000)
        }
      } else if (pos > 0) {
        pos--
        setTypedWord(word.slice(0, pos))
        timer = setTimeout(tick, 50)
      } else {
        deleting = false
        idx = (idx + 1) % DYNAMIC_WORDS.length
        timer = setTimeout(tick, 250)
      }
    }
    timer = setTimeout(tick, 2000)
    return () => clearTimeout(timer)
  }, [])

  // Scroll: parallax + dashboard tilt
  useEffect(() => {
    const onScroll = () => {
      setScrollY(window.scrollY)
      if (dashRef.current) {
        const rect = dashRef.current.getBoundingClientRect()
        const vh = window.innerHeight
        const start = vh * 0.8
        const end = vh * 0.2
        if (rect.top >= start) setDashTilt(0)
        else if (rect.top <= end) setDashTilt(15)
        else setDashTilt(((start - rect.top) / (start - end)) * 15)
      }
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Scroll-reveal IntersectionObserver
  useEffect(() => {
    setIsLoaded(true)
    observerRef.current = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('l2orig-anim-in') }),
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    )
    document.querySelectorAll('.l2orig-anim').forEach(el => observerRef.current.observe(el))
    return () => observerRef.current?.disconnect()
  }, [])

  const goLogin = () => navigate('/login')

  return (
    <div className={`l2orig-root${isLoaded ? ' l2orig-loaded' : ''}`}>

      {/* ── Header ── */}
      <header className={`l2orig-header${scrollY > 50 ? ' l2orig-header--scrolled' : ''}`}>
        <div className="l2orig-header-inner">
          <button className="l2orig-header-logo-btn" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <img src="/logo.png" alt="AgroNexo" className="l2orig-logo-img" />
          </button>

          <button className="l2orig-btn-acceder" onClick={goLogin}>
            Ingresar
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
            </svg>
          </button>

          <button className="l2orig-menu-btn" onClick={() => setIsMenuOpen(v => !v)} aria-label="Menú">
            {isMenuOpen
              ? <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              : <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
            }
          </button>
        </div>
      </header>

      {/* ── Mobile menu overlay ── */}
      {isMenuOpen && (
        <div className="l2orig-mobile-menu">
          <button className="l2orig-mobile-menu-cta" onClick={() => { goLogin(); setIsMenuOpen(false) }}>Ingresar a la plataforma</button>
        </div>
      )}

      {/* ── Hero ── */}
      <section className="l2orig-hero">
        <div
          className="l2orig-hero-parallax"
          style={{ transform: `translateY(${scrollY * 0.4}px)` }}
        />
        <div className="l2orig-hero-gradient" />

        <div
          className="l2orig-hero-content"
          style={{ transform: `translateY(${scrollY * 0.15}px)` }}
        >
          <div className="l2orig-hero-text">
            <h1 className="l2orig-hero-title">
              <span className="l2orig-hero-word l2orig-stagger">
                Gestioná{' '}<span className="l2orig-hero-accent">{typedWord}</span>
              </span>
              <span className="l2orig-stagger l2orig-stagger-2">a escala</span>
            </h1>
            <div className="l2orig-stagger l2orig-stagger-4" style={{ marginTop: '4.5rem' }}>
              <button className="l2orig-btn-hero" onClick={goLogin}>
                <span>Comenzar ahora</span>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Marquee ── */}
      <section className="l2orig-marquee-section">
        <p className="l2orig-marquee-label">Capacidades del motor de precisión agronómica</p>
        <div className="l2orig-marquee">
          <div className="l2orig-marquee-track">
            {[...CAPACIDADES, ...CAPACIDADES].map((item, i) => (
              <span key={i} className="l2orig-marquee-item">
                <span className="l2orig-marquee-dot" />
                {item}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="l2orig-footer">
        <div className="l2orig-container">
          <div className="l2orig-footer-main">
            <div className="l2orig-footer-brand-col">
              <div className="l2orig-footer-brand-header">
                <img src="/logo.png" alt="AgroNexo" className="l2orig-footer-logo-full" />
              </div>
              <p className="l2orig-footer-brand-desc">
                Soluciones de agricultura de precisión, procesamiento GIS y diagnóstico asistido por inteligencia artificial para el NEA argentino.
              </p>
              <div className="l2orig-footer-meta">
                <span className="l2orig-footer-meta-item">
                  Resistencia, Chaco · Argentina
                </span>
              </div>
            </div>

            <div className="l2orig-footer-col">
              <h4 className="l2orig-footer-col-title">MÓDULOS</h4>
              <button className="l2orig-footer-btn" onClick={goLogin}>Motor de Diagnóstico</button>
              <button className="l2orig-footer-btn" onClick={goLogin}>Prescripciones ISO-XML</button>
            </div>

            <div className="l2orig-footer-col">
              <h4 className="l2orig-footer-col-title">PLATAFORMA</h4>
              <button className="l2orig-footer-btn" onClick={goLogin}>Iniciar Sesión</button>
              <button className="l2orig-footer-btn" onClick={goLogin}>Crear Cuenta</button>
            </div>
          </div>

          <div className="l2orig-footer-bottom">
            <span>© 2026 AgroNexo GIS Platform. Todos los derechos reservados.</span>
            <div className="l2orig-footer-bottom-links">
              <a href="#">Términos de Servicio</a>
              <a href="#">Privacidad Geoespacial</a>
              <a href="#">Documentación API</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
