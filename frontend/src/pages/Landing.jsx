import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

/* ── Data ── */
const DYNAMIC_WORDS = ['cultivos', 'lotes', 'datos', 'rendimiento', 'recursos']

const FEATURES = [
  {
    title: 'Captura Multiespectral',
    desc: 'Drones y satélites capturan bandas NIR, RE y Green con sincronización GPS RTK centimétrica.',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
      </svg>
    ),
  },
  {
    title: 'Análisis IA en tiempo real',
    desc: 'Red neuronal que procesa ortomosaicos y genera índices de vegetación precisos al instante.',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>
      </svg>
    ),
  },
  {
    title: 'Diagnóstico de Anomalías',
    desc: 'Detecta focos de estrés hídrico, plagas y deficiencias nutricionales semanas antes que el ojo humano.',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        <line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
      </svg>
    ),
  },
  {
    title: 'Prescripción Diferenciada',
    desc: 'Genera órdenes de trabajo ISO-XML para maquinaria de aplicación variable con buffer geométrico.',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
      </svg>
    ),
  },
]

const FAQS = [
  {
    question: '¿Cómo funciona el monitoreo satelital de AgroNexo?',
    answer: 'Procesamos imágenes multiespectrales de Sentinel-2 y drones DJI Mavic 3 Multispectral. Nuestro pipeline extrae bandas NIR, RED y GREEN para calcular NDVI, NDRE y SAVI con resolución centimétrica, generando alertas automáticas ante variaciones superiores al umbral configurado.',
  },
  {
    question: '¿Qué cultivos y regiones cubre la plataforma?',
    answer: 'AgroNexo está optimizado para soja, algodón, maíz y sorgo en el NEA argentino (Chaco, Formosa, Corrientes). El sistema contempla las particularidades edáficas de vertisoles y suelos sódico-salinos de la región.',
  },
  {
    question: '¿Qué precisión tiene la detección de anomalías?',
    answer: 'Nuestro modelo alcanza 99% de precisión en la clasificación de zonas. Clasificamos patrones espaciales (circulares, lineales, difusos) para diferenciar enfermedades fúngicas, compactación, déficit hídrico y plagas con scoring probabilístico.',
  },
  {
    question: '¿Puedo integrar AgroNexo con mis sistemas existentes?',
    answer: 'Sí. AgroNexo expone una API REST completa con endpoints GeoJSON y exportación a Shapefile, ISO-XML e integración IoT. Compatible con sistemas de autoguiado John Deere y Case IH mediante RTK.',
  },
  {
    question: '¿Cuánto tiempo tarda el procesamiento de un lote?',
    answer: 'El pipeline GIS completo (carga GeoTIFF → índices → vectorización → diagnóstico) tarda entre 2 y 8 minutos según el tamaño del archivo. El progreso es visible en tiempo real mediante polling cada 2 segundos.',
  },
  {
    question: '¿Cómo accedo a los reportes y prescripciones?',
    answer: 'Desde el dashboard podés descargar reportes PDF (WeasyPrint), archivos Shapefile.zip para maquinaria y órdenes ISO-XML para ISOBUS. También están disponibles via API para integración automática con tu flujo de trabajo.',
  },
]

/* ── Component ── */
export default function Landing() {
  const navigate = useNavigate()
  const [isLoaded, setIsLoaded] = useState(false)
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [scrollY, setScrollY] = useState(0)
  const [selectedFeature, setSelectedFeature] = useState(0)
  const [imageFade, setImageFade] = useState(true)
  const [autoRotationKey, setAutoRotationKey] = useState(0)
  const [wordIndex, setWordIndex] = useState(0)
  const [wordFade, setWordFade] = useState(true)
  const [openFaq, setOpenFaq] = useState(null)

  const observerRef = useRef(null)

  // Word rotation
  useEffect(() => {
    const interval = setInterval(() => {
      setWordFade(false)
      setTimeout(() => {
        setWordIndex(i => (i + 1) % DYNAMIC_WORDS.length)
        setWordFade(true)
      }, 300)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  // Scroll: parallax
  useEffect(() => {
    const onScroll = () => setScrollY(window.scrollY)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Scroll-reveal IntersectionObserver
  useEffect(() => {
    setIsLoaded(true)
    observerRef.current = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('l2nd-anim-in') }),
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    )
    document.querySelectorAll('.l2nd-anim').forEach(el => observerRef.current.observe(el))
    return () => observerRef.current?.disconnect()
  }, [])

  // Feature auto-rotation
  useEffect(() => {
    const interval = setInterval(() => {
      setImageFade(false)
      setTimeout(() => {
        setSelectedFeature(i => (i + 1) % FEATURES.length)
        setImageFade(true)
      }, 300)
    }, 6000)
    return () => clearInterval(interval)
  }, [autoRotationKey])

  const scrollTo = id => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
    setIsMenuOpen(false)
  }

  const goLogin = () => navigate('/login')

  return (
    <div className={`l2nd-root${isLoaded ? ' l2nd-loaded' : ''}`}>

      {/* ── Header ── */}
      <header className="l2nd-header">
        <div className="l2nd-header-inner">
          <button className="l2nd-header-logo-btn" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <img src="/logo.png" alt="AgroNexo" className="l2nd-logo-img" />
          </button>

          <nav className="l2nd-nav">
            {[['features','Tecnología'],['faq','FAQ'],['cta','Acceso']].map(([id, label]) => (
              <button key={id} className="l2nd-nav-link" onClick={() => scrollTo(id)}>{label}</button>
            ))}
          </nav>

          <button className="l2nd-btn-acceder" onClick={goLogin}>
            Ingresar
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
            </svg>
          </button>

          <button className="l2nd-menu-btn" onClick={() => setIsMenuOpen(v => !v)} aria-label="Menú">
            {isMenuOpen
              ? <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              : <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
            }
          </button>
        </div>
      </header>

      {/* ── Mobile menu overlay ── */}
      {isMenuOpen && (
        <div className="l2nd-mobile-menu">
          {[['features','Tecnología'],['faq','FAQ'],['cta','Acceso']].map(([id, label]) => (
            <button key={id} className="l2nd-mobile-menu-link" onClick={() => scrollTo(id)}>{label}</button>
          ))}
          <button className="l2nd-mobile-menu-cta" onClick={() => { goLogin(); setIsMenuOpen(false) }}>Ingresar a la plataforma</button>
        </div>
      )}

      {/* ── Hero ── */}
      <section className="l2nd-hero">
        <div className="l2nd-hero-top">
          <div
            className="l2nd-hero-parallax"
            style={{ transform: `translateY(${scrollY * 0.4}px)` }}
          />
          <div className="l2nd-hero-gradient" />

          <h1
            className="l2nd-hero-headline"
            style={{ transform: `translateY(${scrollY * 0.15}px)` }}
          >
            <span className={`l2nd-hero-word l2nd-stagger${wordFade ? '' : ' l2nd-word-hidden'}`}>
              Gestioná <span className="l2nd-hero-accent">{DYNAMIC_WORDS[wordIndex]}</span>
            </span>
            <span className="l2nd-stagger l2nd-stagger-2">a escala</span>
          </h1>
        </div>

        <div className="l2nd-hero-bottom">
          <div className="l2nd-hero-card l2nd-stagger l2nd-stagger-3">
            <div className="l2nd-hero-text">
              <span className="l2nd-hero-eyebrow">Diagnóstico agronómico con IA</span>
              <h2 className="l2nd-hero-title">Lo que ocurre en tu lote</h2>
              <p className="l2nd-hero-desc">
                Ortomosaicos de dron + índices espectrales (NDVI, NDRE, SAVI) que detectan
                estrés hídrico, plagas y enfermedades por zona, no por lote entero.
              </p>
              <button className="l2nd-btn-hero" onClick={goLogin}>
                Analizar mi primer lote
              </button>
            </div>

            <div className="l2nd-hero-visual">
              <img
                src="/dashboard.jpeg"
                alt="Dashboard de diagnóstico de AgroNexo en un laptop"
                className="l2nd-hero-laptop"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="l2nd-section l2nd-anim">
        <div className="l2nd-container">
          <div className="l2nd-features-grid">
            {/* Left: text + feature list */}
            <div>
              <div className="l2nd-eyebrow">
                <span className="l2nd-eyebrow-dot" />
                TECNOLOGÍA GIS
              </div>
              <h2 className="l2nd-features-title">
                Cada lote agrícola{' '}
                <span className="l2nd-gradient-text">importa</span>
              </h2>
              <p className="l2nd-features-desc">
                Nuestra plataforma satelital con IA monitorea la biodiversidad del suelo, detecta
                anomalías fitosanitarias, y alerta en tiempo real. Precisión al ritmo que exige el campo.
              </p>

              {/* Mobile: single image */}
              <div className="l2nd-features-img-mobile">
                <img
                  src="/fondo.jpeg"
                  alt="Feature"
                  style={{ opacity: imageFade ? 1 : 0, transition: 'opacity 0.3s' }}
                />
              </div>

              <div className="l2nd-features-list">
                {FEATURES.map((f, i) => (
                  <button
                    key={i}
                    className={`l2nd-feature-item${selectedFeature === i ? ' l2nd-feature-item--active' : ''}`}
                    onClick={() => {
                      setImageFade(false)
                      setTimeout(() => { setSelectedFeature(i); setImageFade(true); setAutoRotationKey(k => k + 1) }, 300)
                    }}
                  >
                    <span className={`l2nd-feature-icon${selectedFeature === i ? ' l2nd-feature-icon--active' : ''}`}>
                      {f.icon}
                    </span>
                    <div>
                      <h3 className="l2nd-feature-title">{f.title}</h3>
                      <p className="l2nd-feature-desc">{f.desc}</p>
                    </div>
                    {selectedFeature === i && (
                      <div className="l2nd-progress-track">
                        <div className="l2nd-progress-bar" />
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Right: image stack */}
            <div className="l2nd-img-stack">
              {FEATURES.map((_, i) => {
                const pos = (i - selectedFeature + FEATURES.length) % FEATURES.length
                return (
                  <div
                    key={i}
                    className="l2nd-img-stack-item"
                    style={{
                      zIndex: FEATURES.length - pos,
                      transform: `translateX(${pos * 18}px) scale(${1 - pos * 0.025})`,
                      opacity: pos === 0 ? (imageFade ? 1 : 0.8) : Math.max(0, 0.55 - pos * 0.15),
                      transition: 'all 0.6s cubic-bezier(0.16,1,0.3,1)',
                    }}
                  >
                    <img src="/fondo.jpeg" alt={FEATURES[i].title} />
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section id="faq" className="l2nd-section l2nd-anim">
        <div className="l2nd-container l2nd-container--narrow">
          <div className="l2nd-section-center">
            <div className="l2nd-eyebrow l2nd-eyebrow--center">
              <span className="l2nd-eyebrow-dot" />
              PREGUNTAS FRECUENTES
            </div>
            <h2 className="l2nd-section-title">
              ¿Tenés <span className="l2nd-gradient-text">preguntas</span>?
            </h2>
            <p className="l2nd-section-desc">
              Todo lo que necesitás saber sobre AgroNexo y nuestra plataforma de precisión agronómica.
            </p>
          </div>

          <div className="l2nd-faq-list">
            {FAQS.map((faq, i) => (
              <div key={i} className={`l2nd-faq-item${openFaq === i ? ' l2nd-faq-item--open' : ''}`}>
                <button
                  className="l2nd-faq-question"
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                >
                  <span>{faq.question}</span>
                  <svg
                    className={`l2nd-faq-chevron${openFaq === i ? ' l2nd-faq-chevron--open' : ''}`}
                    width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                  >
                    <polyline points="6 9 12 15 18 9"/>
                  </svg>
                </button>
                <div className={`l2nd-faq-answer${openFaq === i ? ' l2nd-faq-answer--open' : ''}`}>
                  <p>{faq.answer}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section id="cta" className="l2nd-cta l2nd-anim">
        <div className="l2nd-cta-gradient-top" />
        <div className="l2nd-cta-bg" />
        <div className="l2nd-container l2nd-cta-content">
          <div className="l2nd-cta-pill">
            <span className="l2nd-eyebrow-dot" />
            Plataforma de precisión agronómica
          </div>
          <h2 className="l2nd-cta-title">Uníte al movimiento de agricultura digital</h2>
          <p className="l2nd-cta-desc">
            Junto a productores líderes del NEA estamos transformando la toma de decisiones
            en el campo con tecnología GIS de precisión.
          </p>
          <button className="l2nd-btn-cta" onClick={goLogin}>
            Acceder a la plataforma
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="l2nd-footer">
        <div className="l2nd-container">
          <div className="l2nd-footer-grid">
            <div className="l2nd-footer-brand">
              <img src="/logo_verde.png" alt="AgroNexo" className="l2nd-footer-logo" />
              <p className="l2nd-footer-brand-desc">
                Liderando la revolución de la agricultura digital con soluciones geoespaciales de alta precisión.
              </p>
              <div className="l2nd-footer-social">
                {/* X */}
                <a href="#" className="l2nd-social-link" aria-label="X">
                  <svg width="15" height="15" fill="currentColor" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                </a>
                {/* YouTube */}
                <a href="#" className="l2nd-social-link" aria-label="YouTube">
                  <svg width="15" height="15" fill="currentColor" viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
                </a>
                {/* Instagram */}
                <a href="#" className="l2nd-social-link" aria-label="Instagram">
                  <svg width="15" height="15" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/></svg>
                </a>
              </div>
            </div>

            <div className="l2nd-footer-col">
              <h4 className="l2nd-footer-col-title">Producto</h4>
              {['Funcionalidades','Precios','Documentación','API GIS'].map(l => <a key={l} href="#" className="l2nd-footer-link">{l}</a>)}
            </div>

            <div className="l2nd-footer-col">
              <h4 className="l2nd-footer-col-title">Compañía</h4>
              {['Sobre Nosotros','Blog Técnico','Casos de Éxito','Contacto'].map(l => <a key={l} href="#" className="l2nd-footer-link">{l}</a>)}
            </div>

            <div className="l2nd-footer-col">
              <h4 className="l2nd-footer-col-title">Newsletter</h4>
              <p className="l2nd-footer-newsletter-desc">Novedades sobre agricultura de precisión en el NEA.</p>
              <input type="email" placeholder="tu@email.com" className="l2nd-newsletter-input" />
              <button className="l2nd-newsletter-btn">Suscribirse</button>
            </div>
          </div>

          <div className="l2nd-footer-bottom">
            <span>© 2026 AgroNexo GIS Solutions. Todos los derechos reservados.</span>
            <div className="l2nd-footer-bottom-links">
              <a href="#">Privacidad</a>
              <a href="#">Términos</a>
              <a href="#">Cookies</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
