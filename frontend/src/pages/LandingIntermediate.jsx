import './LandingIntermediate.css'
import { useEffect, useRef, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'

/* ── Animated Counter Component ── */
function AnimatedCounter({ value, prefix = '', suffix = '' }) {
  const [display, setDisplay] = useState('0')
  const ref = useRef(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        const numStr = value.replace(/[^0-9.]/g, '')
        const target = parseFloat(numStr)
        if (isNaN(target)) {
          setDisplay(value)
          return
        }
        let current = 0
        const step = target / 50
        const interval = setInterval(() => {
          current += step
          if (current >= target) {
            setDisplay(target % 1 === 0 ? target.toString() : target.toFixed(1))
            clearInterval(interval)
          } else {
            setDisplay(current >= 10 ? Math.floor(current).toString() : current.toFixed(1))
          }
        }, 20)
        observer.disconnect()
      },
      { threshold: 0.3 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [value])

  return (
    <span ref={ref} className="l2mid-counter-val">
      {prefix}{display}{suffix}
    </span>
  )
}

/* ── Data Constants ── */
const DYNAMIC_WORDS = ['cultivos', 'lotes agrícolas', 'rendimientos', 'recursos', 'decisiones']

const METRICS = [
  { label: 'Lotes Procesados', num: '1250', suffix: '+', desc: 'campos monitoreados en el NEA', accent: 'emerald' },
  { label: 'Índices Calculados', num: '45', suffix: 'K', desc: 'análisis NDVI, NDRE y SAVI', accent: 'lime' },
  { label: 'Ahorro de Insumos', num: '28', suffix: '%', desc: 'reducción promedio en fertilizantes', accent: 'cyan' },
  { label: 'Precisión Diagnóstica', num: '99.4', suffix: '%', desc: 'exactitud en detección de anomalías', accent: 'emerald' },
]

const PIPELINE_STEPS = [
  {
    id: 'captura',
    step: '01',
    title: 'Captura Multiespectral',
    subtitle: 'Satélite Sentinel-2 & Drones RTK',
    desc: 'Integración continua de pasadas satelitales cada 5 días y vuelos de drones con sensores multiespectrales (NIR, Red Edge, Green). Georreferenciación centimétrica en proyección EPSG:32721.',
    badge: 'Resolución Centimétrica',
    features: ['Soporte GeoTIFF multibanda', 'Pasadas Sentinel-2 automáticas', 'Corrección atmosférica BOA'],
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polygon points="12 2 2 7 12 12 22 7 12 2" />
        <polyline points="2 17 12 22 22 17" />
        <polyline points="2 12 12 17 22 12" />
      </svg>
    ),
  },
  {
    id: 'indices',
    step: '02',
    title: 'Procesamiento GIS & Índices',
    subtitle: 'Pipeline Celery + Rasterio en Paralelo',
    desc: 'Cálculo simultáneo de NDVI, NDRE, SAVI y ExG. Umbralización adaptativa (Otsu y percentil) y vectorización de polígonos homogéneos con filtrado de ruido y conectividad 8.',
    badge: 'Multi-índice Paralelo',
    features: ['NDVI / NDRE / SAVI / ExG', 'Umbralización Otsu / Fija / Percentil', 'Detección de Zonas Atípicas (Z-Score)'],
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="3" />
        <path d="M3 9h18M9 21V9" />
      </svg>
    ),
  },
  {
    id: 'diagnostico',
    step: '03',
    title: 'Motor de Diagnóstico con IA',
    subtitle: '20+ Reglas Agronómicas Regionales',
    desc: 'Evaluación inteligente que combina morfología de manchas, variabilidad espacial y base de datos fitosanitaria para identificar estrés hídrico, compactación, malezas o deficiencias nutricionales.',
    badge: 'Expertise NEA',
    features: ['Clasificación por severidad (Crítica, Media, Leve)', 'Zonificación de Unidades de Manejo', 'Prescripción de fitosanitarios por causa'],
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
  },
  {
    id: 'prescripcion',
    step: '04',
    title: 'Prescripción & Aplicación Variable',
    subtitle: 'Compatibilidad con Maquinaria & Reportes',
    desc: 'Exportación instantánea de prescripciones de dosis variable en formatos estándar Shapefile e ISO-XML para computadoras de pulverizadoras y sembradoras, junto a reportes ejecutivos en PDF.',
    badge: 'Listo para Campo',
    features: ['Reportes PDF automáticos', 'Exportación Shapefile / GeoJSON', 'Compatible con John Deere, Case IH y Trimble'],
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    ),
  },
]

const CROPS_DATA = [
  { id: 'soja', name: 'Soja', baseCostHa: 180, potentialSavingPct: 0.22, yieldGainPct: 0.08, priceTon: 340, avgYieldHa: 3.2 },
  { id: 'maiz', name: 'Maíz', baseCostHa: 260, potentialSavingPct: 0.25, yieldGainPct: 0.10, priceTon: 190, avgYieldHa: 8.5 },
  { id: 'algodon', name: 'Algodón', baseCostHa: 310, potentialSavingPct: 0.28, yieldGainPct: 0.12, priceTon: 620, avgYieldHa: 2.8 },
  { id: 'sorgo', name: 'Sorgo', baseCostHa: 140, potentialSavingPct: 0.20, yieldGainPct: 0.07, priceTon: 160, avgYieldHa: 5.5 },
]

const HOTSPOTS_DATA = [
  { id: 1, top: '28%', left: '32%', label: 'Zona Norte', status: 'Estrés Hídrico', ndvi: '0.38', color: '#ef4444', desc: 'Déficit hídrico detectado en vertisol con pendiente leve.' },
  { id: 2, top: '45%', left: '68%', label: 'Zona Este', status: 'Óptimo', ndvi: '0.84', color: '#6db88a', desc: 'Vigor vegetal alto. Excelente respuesta a fertilización nitrogenada.' },
  { id: 3, top: '72%', left: '40%', label: 'Bajo Central', status: 'Anomalía Media', ndvi: '0.52', color: '#f59e0b', desc: 'Posible enmalezamiento localizado en cabecera.' },
]

const FAQS = [
  {
    q: '¿Cómo se procesan las imágenes satelitales y de drones en AgroNexo?',
    a: 'Nuestra plataforma ingesta ortomosaicos GeoTIFF de drones (DJI, eBee, etc.) y pasadas satelitales Sentinel-2 de la ESA. El motor de procesamiento en Celery extrae las bandas espectrales (NIR, Red, RedEdge, Green), calcula los índices de vegetación a nivel de píxel y vectoriza automáticamente las zonas con umbrales adaptativos.',
  },
  {
    q: '¿Qué diferencia a AgroNexo de otros visores NDVI convencionales?',
    a: 'AgroNexo no se limita a mostrar mapas de colores; incorpora un motor de diagnóstico agronómico entrenado con más de 20 reglas específicas para suelos y cultivos del NEA argentino (Chaco, Formosa, Corrientes, Santa Fe Norte), agrupando polígonos contiguos en Unidades de Manejo accionables y recomendando productos fitosanitarios específicos.',
  },
  {
    q: '¿Qué formatos de exportación son compatibles con mi maquinaria?',
    a: 'Podés exportar prescripciones en formato Shapefile (.shp / .zip) e ISO-XML compatibles con monitores y controladores de aplicación variable de marcas líderes como John Deere (GS3, Gen4), Case IH (AFS Pro), Trimble, Raven y Yomel, además de reportes PDF ejecutivos listos para imprimir.',
  },
  {
    q: '¿Cuánto tiempo tarda en procesarse un vuelo completo?',
    a: 'Un GeoTIFF de 500 MB (100 a 300 hectáreas a resolución centimétrica) se procesa en segundo plano en menos de 2 a 4 minutos, calculando simultáneamente NDVI, NDRE, SAVI y ExG con barra de progreso en vivo.',
  },
  {
    q: '¿Puedo dibujar o importar los límites de mis lotes?',
    a: 'Sí. Podés dibujar tus lotes directamente sobre el mapa satelital interactivo, ingresar coordenadas de vértices, o dejar que el sistema extraiga automáticamente el límite geográfico a partir del bounding box del ortomosaico cargado.',
  },
]

const INTEGRATIONS = [
  'Sentinel-2 ESA',
  'DJI Enterprise',
  'John Deere Operations',
  'Case IH AFS',
  'Trimble Agriculture',
  'PostGIS & GDAL',
  'WeasyPrint PDF',
  'ISO-XML Standards'
]

export default function LandingIntermediate() {
  const navigate = useNavigate()
  const [activeLayer, setActiveLayer] = useState('ndvi') // 'rgb' | 'ndvi' | 'ndre' | 'zonas'
  const [selectedHotspot, setSelectedHotspot] = useState(HOTSPOTS_DATA[1])
  const [sliderPosition, setSliderPosition] = useState(50)
  const [isDraggingSlider, setIsDraggingSlider] = useState(false)
  const [activeStep, setActiveStep] = useState(0)
  const [wordIndex, setWordIndex] = useState(0)
  const [wordFade, setWordFade] = useState(true)
  const [selectedCrop, setSelectedCrop] = useState(CROPS_DATA[0])
  const [hectares, setHectares] = useState(350)
  const [openFaq, setOpenFaq] = useState(0)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const sliderContainerRef = useRef(null)

  // Dynamic word rotation
  useEffect(() => {
    const timer = setInterval(() => {
      setWordFade(false)
      setTimeout(() => {
        setWordIndex((prev) => (prev + 1) % DYNAMIC_WORDS.length)
        setWordFade(true)
      }, 300)
    }, 3200)
    return () => clearInterval(timer)
  }, [])

  // Auto step rotation in pipeline
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % PIPELINE_STEPS.length)
    }, 7000)
    return () => clearInterval(timer)
  }, [])

  // Slider drag handler
  const handleSliderMove = (e) => {
    if (!sliderContainerRef.current) return
    const rect = sliderContainerRef.current.getBoundingClientRect()
    const clientX = e.touches ? e.touches[0].clientX : e.clientX
    const offsetX = Math.max(0, Math.min(clientX - rect.left, rect.width))
    const pct = Math.round((offsetX / rect.width) * 100)
    setSliderPosition(pct)
  }

  const handleTouchMove = (e) => {
    if (isDraggingSlider) handleSliderMove(e)
  }

  useEffect(() => {
    const onMouseUp = () => setIsDraggingSlider(false)
    const onMouseMove = (e) => {
      if (isDraggingSlider) handleSliderMove(e)
    }

    if (isDraggingSlider) {
      window.addEventListener('mousemove', onMouseMove)
      window.addEventListener('mouseup', onMouseUp)
    }
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [isDraggingSlider])

  // ROI calculations
  const roiResults = useMemo(() => {
    const inputSaving = hectares * selectedCrop.baseCostHa * selectedCrop.potentialSavingPct
    const yieldIncrementTons = hectares * (selectedCrop.avgYieldHa * selectedCrop.yieldGainPct)
    const extraRevenue = yieldIncrementTons * selectedCrop.priceTon
    const totalBenefit = inputSaving + extraRevenue
    const platformCostYear = Math.max(480, hectares * 2.5)
    const netProfit = totalBenefit - platformCostYear
    const roiMultiplier = (totalBenefit / platformCostYear).toFixed(1)

    return {
      inputSaving: Math.round(inputSaving).toLocaleString('es-AR'),
      extraRevenue: Math.round(extraRevenue).toLocaleString('es-AR'),
      totalBenefit: Math.round(totalBenefit).toLocaleString('es-AR'),
      netProfit: Math.round(netProfit).toLocaleString('es-AR'),
      roiMultiplier,
    }
  }, [hectares, selectedCrop])

  const scrollToSection = (id) => {
    setMobileMenuOpen(false)
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <div className="l2mid-page">
      {/* ── Background Glow Elements ── */}
      <div className="l2mid-bg-glow l2mid-bg-glow-top" />
      <div className="l2mid-bg-glow l2mid-bg-glow-center" />
      <div className="l2mid-grid-overlay" />

      {/* ── Navigation Bar ── */}
      <header className="l2mid-navbar-wrap">
        <div className="l2mid-navbar">
          <div className="l2mid-nav-brand" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <img src="/logo_hoja.png" alt="AgroNexo Leaf" className="l2mid-nav-logo-icon" />
            <span className="l2mid-nav-brand-text">
              Agro<span className="l2mid-accent-text">Nexo</span>
            </span>
            <span className="l2mid-nav-tag">GIS v3.0</span>
          </div>

          <nav className="l2mid-nav-links">
            <button className="l2mid-nav-btn" onClick={() => scrollToSection('demo-interactiva')}>Simulador</button>
            <button className="l2mid-nav-btn" onClick={() => scrollToSection('comparador')}>Comparador</button>
            <button className="l2mid-nav-btn" onClick={() => scrollToSection('pipeline')}>Tecnología</button>
            <button className="l2mid-nav-btn" onClick={() => scrollToSection('roi-calculator')}>Calculadora ROI</button>
            <button className="l2mid-nav-btn" onClick={() => scrollToSection('faq')}>Preguntas</button>
          </nav>

          <div className="l2mid-nav-actions">
            <button className="l2mid-btn-ghost" onClick={() => navigate('/login')}>
              Iniciar Sesión
            </button>
            <button className="l2mid-btn-primary l2mid-btn-nav" onClick={() => navigate('/login')}>
              <span>Acceder al Sistema</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
            <button
              className="l2mid-menu-toggle"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Abrir menú"
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {mobileMenuOpen ? (
                  <path d="M18 6L6 18M6 6l12 12" />
                ) : (
                  <path d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile menu dropdown */}
        {mobileMenuOpen && (
          <div className="l2mid-mobile-nav">
            <button className="l2mid-mobile-nav-link" onClick={() => scrollToSection('demo-interactiva')}>Simulador de Índices</button>
            <button className="l2mid-mobile-nav-link" onClick={() => scrollToSection('comparador')}>Comparador RGB vs NDVI</button>
            <button className="l2mid-mobile-nav-link" onClick={() => scrollToSection('pipeline')}>Pipeline GIS</button>
            <button className="l2mid-mobile-nav-link" onClick={() => scrollToSection('roi-calculator')}>Calculadora de Ahorro</button>
            <button className="l2mid-mobile-nav-link" onClick={() => scrollToSection('faq')}>Preguntas Frecuentes</button>
            <div className="l2mid-mobile-nav-footer">
              <button className="l2mid-btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={() => navigate('/login')}>
                Ingresar a la Plataforma
              </button>
            </div>
          </div>
        )}
      </header>

      {/* ── HERO SECTION ── */}
      <section className="l2mid-hero-section">
        <div className="l2mid-hero-container">
          <div className="l2mid-hero-badge">
            <span className="l2mid-badge-pulse" />
            <span>Monitoreo Satelital & Drones en el NEA</span>
            <span className="l2mid-badge-pill">IA Agronómica</span>
          </div>

          <h1 className="l2mid-hero-heading">
            Gestioná tus{' '}
            <span className={`l2mid-dynamic-word ${wordFade ? 'l2mid-word-visible' : 'l2mid-word-fading'}`}>
              {DYNAMIC_WORDS[wordIndex]}
            </span>
            <br />
            con precisión geoespacial.
          </h1>

          <p className="l2mid-hero-subheading">
            Transformá ortomosaicos multiespectrales y pasadas Sentinel-2 en diagnósticos agronómicos
            precisos, zonificaciones automáticas y prescripciones de dosis variable en tiempo real.
          </p>

          <div className="l2mid-hero-cta-group">
            <button className="l2mid-btn-primary l2mid-btn-hero" onClick={() => navigate('/login')}>
              <span>Comenzar Ahora</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
            <button className="l2mid-btn-secondary l2mid-btn-hero" onClick={() => scrollToSection('demo-interactiva')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              <span>Ver Demo Interactiva</span>
            </button>
          </div>

          {/* Quick stats ribbon */}
          <div className="l2mid-hero-ribbon">
            <div className="l2mid-ribbon-item">
              <span className="l2mid-ribbon-val">Sentinel-2 & Dron</span>
              <span className="l2mid-ribbon-lbl">Entrada Dual de Imágenes</span>
            </div>
            <div className="l2mid-ribbon-divider" />
            <div className="l2mid-ribbon-item">
              <span className="l2mid-ribbon-val">NDVI · NDRE · SAVI · ExG</span>
              <span className="l2mid-ribbon-lbl">Multi-Índice Paralelo</span>
            </div>
            <div className="l2mid-ribbon-divider" />
            <div className="l2mid-ribbon-item">
              <span className="l2mid-ribbon-val">ISO-XML & Shapefile</span>
              <span className="l2mid-ribbon-lbl">Exportación a Maquinaria</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── INTERACTIVE DEMO (HERO VISUALIZER) ── */}
      <section id="demo-interactiva" className="l2mid-section l2mid-visualizer-section">
        <div className="l2mid-section-header">
          <div className="l2mid-section-tag">SIMULADOR EN VIVO</div>
          <h2 className="l2mid-section-title">Visualizador Geoespacial Multiespectral</h2>
          <p className="l2mid-section-desc">
            Alterná entre capas satelitales e interactuá con los focos de diagnóstico detectados por nuestro motor IA.
          </p>
        </div>

        <div className="l2mid-visualizer-card">
          {/* Top Control Bar */}
          <div className="l2mid-viz-toolbar">
            <div className="l2mid-viz-meta">
              <div className="l2mid-viz-live-indicator">
                <span className="l2mid-live-dot" />
                <span>LOTE "LA ESPERANZA #04" · 142.8 ha · SOJA R3</span>
              </div>
            </div>

            {/* Layer Switcher */}
            <div className="l2mid-viz-layers">
              {[
                { id: 'rgb', label: 'Color Real (RGB)', tag: 'Sensor' },
                { id: 'ndvi', label: 'NDVI (Vigor)', tag: 'Índice' },
                { id: 'ndre', label: 'NDRE (Clorofila)', tag: 'Estrés' },
                { id: 'zonas', label: 'Zonificación', tag: 'Manejo' },
              ].map((layer) => (
                <button
                  key={layer.id}
                  className={`l2mid-layer-tab ${activeLayer === layer.id ? 'l2mid-layer-tab--active' : ''}`}
                  onClick={() => setActiveLayer(layer.id)}
                >
                  <span className="l2mid-layer-label">{layer.label}</span>
                  <span className="l2mid-layer-tag">{layer.tag}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Map & Visual Canvas */}
          <div className="l2mid-viz-canvas">
            {/* Background Map Simulation depending on layer */}
            <div className={`l2mid-map-viewport l2mid-layer-${activeLayer}`}>
              <img
                src="/fondo.jpeg"
                alt="Simulación Geoespacial AgroNexo"
                className="l2mid-map-bg-img"
              />
              <div className={`l2mid-map-spectral-filter l2mid-filter-${activeLayer}`} />

              {/* Vector Grid & Contours simulation */}
              <div className="l2mid-map-vector-overlay" />

              {/* Hotspots */}
              {HOTSPOTS_DATA.map((spot) => (
                <div
                  key={spot.id}
                  className={`l2mid-hotspot ${selectedHotspot.id === spot.id ? 'l2mid-hotspot--active' : ''}`}
                  style={{ top: spot.top, left: spot.left }}
                  onClick={() => setSelectedHotspot(spot)}
                >
                  <div className="l2mid-hotspot-beacon" style={{ borderColor: spot.color }} />
                  <div className="l2mid-hotspot-core" style={{ backgroundColor: spot.color }} />
                  <div className="l2mid-hotspot-pulse" style={{ backgroundColor: spot.color }} />
                  <span className="l2mid-hotspot-badge">{spot.label}</span>
                </div>
              ))}

              {/* Floating Live Telemetry HUD */}
              <div className="l2mid-viz-hud">
                <div className="l2mid-hud-header">
                  <span className="l2mid-hud-title">Telemetría de Vuelo</span>
                  <span className="l2mid-hud-status">PROCESADO · 100%</span>
                </div>
                <div className="l2mid-hud-grid">
                  <div className="l2mid-hud-stat">
                    <span className="l2mid-hud-stat-lbl">Índice Promedio</span>
                    <span className="l2mid-hud-stat-val">
                      {activeLayer === 'ndvi' ? '0.74 NDVI' : activeLayer === 'ndre' ? '0.62 NDRE' : '0.68 SAVI'}
                    </span>
                  </div>
                  <div className="l2mid-hud-stat">
                    <span className="l2mid-hud-stat-lbl">Zonas Homogéneas</span>
                    <span className="l2mid-hud-stat-val">5 Unidades</span>
                  </div>
                  <div className="l2mid-hud-stat">
                    <span className="l2mid-hud-stat-lbl">Variabilidad (CV)</span>
                    <span className="l2mid-hud-stat-val">14.2%</span>
                  </div>
                  <div className="l2mid-hud-stat">
                    <span className="l2mid-hud-stat-lbl">Resolución</span>
                    <span className="l2mid-hud-stat-val">4.5 cm/px</span>
                  </div>
                </div>

                {/* Color Legend Scale */}
                <div className="l2mid-hud-legend">
                  <div className="l2mid-legend-labels">
                    <span>Bajo Vigor (0.1)</span>
                    <span>Medio (0.5)</span>
                    <span>Óptimo (0.9)</span>
                  </div>
                  <div className={`l2mid-legend-bar l2mid-legend-${activeLayer}`} />
                </div>
              </div>

              {/* Selected Hotspot Detail Card */}
              {selectedHotspot && (
                <div className="l2mid-hotspot-card">
                  <div className="l2mid-hotspot-card-header">
                    <div>
                      <span className="l2mid-hotspot-card-zone">{selectedHotspot.label}</span>
                      <h4 className="l2mid-hotspot-card-status" style={{ color: selectedHotspot.color }}>
                        {selectedHotspot.status}
                      </h4>
                    </div>
                    <div className="l2mid-hotspot-card-badge">
                      <span>NDVI</span>
                      <strong>{selectedHotspot.ndvi}</strong>
                    </div>
                  </div>
                  <p className="l2mid-hotspot-card-desc">{selectedHotspot.desc}</p>
                  <div className="l2mid-hotspot-card-action">
                    <button className="l2mid-btn-link" onClick={() => navigate('/login')}>
                      Generar prescripción para este sector →
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── BEFORE & AFTER INTERACTIVE SLIDER ── */}
      <section id="comparador" className="l2mid-section l2mid-slider-section">
        <div className="l2mid-section-header">
          <div className="l2mid-section-tag">TECNOLOGÍA DE DETECCIÓN</div>
          <h2 className="l2mid-section-title">De Imagen Aérea a Diagnóstico Agronómico</h2>
          <p className="l2mid-section-desc">
            Arrastrá el divisor interactivo para comparar la vista en color natural frente al mapa térmico de índice NDVI procesado con vectorización.
          </p>
        </div>

        <div
          ref={sliderContainerRef}
          className="l2mid-split-container"
          onMouseDown={() => setIsDraggingSlider(true)}
          onTouchStart={() => setIsDraggingSlider(true)}
          onTouchMove={handleTouchMove}
        >
          {/* Background Left: RGB Image */}
          <div className="l2mid-split-layer l2mid-split-rgb">
            <img src="/fondo.jpeg" alt="Fotografía RGB convencional" className="l2mid-split-img" />
            <div className="l2mid-split-tag l2mid-split-tag-left">
              <span>📷 CÁMARA RGB CONVENCIONAL</span>
              <small>El estrés hídrico y las deficiencias son casi imperceptibles a simple vista</small>
            </div>
          </div>

          {/* Foreground Right: NDVI Analyzed (Clipped) */}
          <div
            className="l2mid-split-layer l2mid-split-ndvi"
            style={{ clipPath: `polygon(${sliderPosition}% 0, 100% 0, 100% 100%, ${sliderPosition}% 100%)` }}
          >
            <img src="/fondo.jpeg" alt="Análisis multiespectral NDVI" className="l2mid-split-img" />
            <div className="l2mid-split-ndvi-overlay" />
            <div className="l2mid-split-tag l2mid-split-tag-right">
              <span>🛰️ ANÁLISIS MULTIESPECTRAL AGRONEXO</span>
              <small>Detección anticipada de anomalías con clasificación de severidad y prescripción</small>
            </div>
          </div>

          {/* Draggable Divider Handle */}
          <div
            className="l2mid-split-handle"
            style={{ left: `${sliderPosition}%` }}
          >
            <div className="l2mid-split-handle-line" />
            <div className="l2mid-split-handle-button">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="15 18 9 12 15 6" />
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </div>
            <div className="l2mid-split-handle-line" />
          </div>
        </div>
      </section>

      {/* ── METRICS & IMPACT ── */}
      <section className="l2mid-section l2mid-metrics-section">
        <div className="l2mid-container">
          <div className="l2mid-metrics-grid">
            {METRICS.map((m, i) => (
              <div key={i} className={`l2mid-metric-card l2mid-metric-card--${m.accent}`}>
                <div className="l2mid-metric-header">
                  <span className={`l2mid-metric-indicator l2mid-ind-${m.accent}`} />
                  <span className="l2mid-metric-title">{m.label}</span>
                </div>
                <div className="l2mid-metric-counter">
                  <AnimatedCounter value={m.num} suffix={m.suffix} />
                </div>
                <p className="l2mid-metric-description">{m.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PIPELINE WORKFLOW (4 STEPS) ── */}
      <section id="pipeline" className="l2mid-section l2mid-pipeline-section">
        <div className="l2mid-section-header">
          <div className="l2mid-section-tag">ARQUITECTURA DE PROCESAMIENTO</div>
          <h2 className="l2mid-section-title">El Pipeline Agronómico en 4 Etapas</h2>
          <p className="l2mid-section-desc">
            Diseñado con tecnología GIS de alto rendimiento, workers asíncronos y algoritmos probados en el campo.
          </p>
        </div>

        <div className="l2mid-container">
          <div className="l2mid-pipeline-grid">
            {/* Step Selection List */}
            <div className="l2mid-pipeline-nav">
              {PIPELINE_STEPS.map((step, idx) => (
                <button
                  key={step.id}
                  className={`l2mid-step-card ${activeStep === idx ? 'l2mid-step-card--active' : ''}`}
                  onClick={() => setActiveStep(idx)}
                >
                  <div className="l2mid-step-num">{step.step}</div>
                  <div className="l2mid-step-body">
                    <div className="l2mid-step-title-row">
                      <span className="l2mid-step-title">{step.title}</span>
                      <span className="l2mid-step-badge">{step.badge}</span>
                    </div>
                    <p className="l2mid-step-sub">{step.subtitle}</p>
                  </div>
                  <div className="l2mid-step-icon">{step.icon}</div>
                  {activeStep === idx && <div className="l2mid-step-indicator-bar" />}
                </button>
              ))}
            </div>

            {/* Step Dynamic Preview Display */}
            <div className="l2mid-pipeline-display">
              <div className="l2mid-pipeline-preview-card">
                <div className="l2mid-preview-header">
                  <div className="l2mid-preview-phase">ETAPA {PIPELINE_STEPS[activeStep].step}</div>
                  <h3 className="l2mid-preview-title">{PIPELINE_STEPS[activeStep].title}</h3>
                  <p className="l2mid-preview-desc">{PIPELINE_STEPS[activeStep].desc}</p>
                </div>

                <div className="l2mid-preview-features">
                  <span className="l2mid-preview-feat-lbl">Capacidades Destacadas:</span>
                  <ul className="l2mid-preview-feat-list">
                    {PIPELINE_STEPS[activeStep].features.map((feat, i) => (
                      <li key={i} className="l2mid-preview-feat-item">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6db88a" strokeWidth="2.5">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        <span>{feat}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="l2mid-preview-action">
                  <button className="l2mid-btn-primary" onClick={() => navigate('/login')}>
                    <span>Explorar en el Dashboard</span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── ROI & SAVINGS CALCULATOR ── */}
      <section id="roi-calculator" className="l2mid-section l2mid-roi-section">
        <div className="l2mid-section-header">
          <div className="l2mid-section-tag">CALCULADORA DE RENTABILIDAD</div>
          <h2 className="l2mid-section-title">Calculá tu Ahorro Estimado</h2>
          <p className="l2mid-section-desc">
            Ajustá las hectáreas y tu cultivo principal para estimar el impacto económico directo de la aplicación variable y el diagnóstico temprano.
          </p>
        </div>

        <div className="l2mid-container l2mid-container--narrow">
          <div className="l2mid-roi-card">
            <div className="l2mid-roi-controls">
              {/* Crop Selector */}
              <div className="l2mid-roi-group">
                <label className="l2mid-roi-label">1. Seleccioná tu Cultivo:</label>
                <div className="l2mid-crop-buttons">
                  {CROPS_DATA.map((crop) => (
                    <button
                      key={crop.id}
                      className={`l2mid-crop-btn ${selectedCrop.id === crop.id ? 'l2mid-crop-btn--active' : ''}`}
                      onClick={() => setSelectedCrop(crop)}
                    >
                      <span>{crop.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Hectares Slider */}
              <div className="l2mid-roi-group">
                <div className="l2mid-roi-slider-header">
                  <label className="l2mid-roi-label">2. Superficie a Monitorear:</label>
                  <span className="l2mid-roi-ha-val">{hectares.toLocaleString('es-AR')} ha</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="3000"
                  step="25"
                  value={hectares}
                  onChange={(e) => setHectares(Number(e.target.value))}
                  className="l2mid-roi-range"
                />
                <div className="l2mid-range-ticks">
                  <span>50 ha</span>
                  <span>500 ha</span>
                  <span>1.500 ha</span>
                  <span>3.000 ha</span>
                </div>
              </div>
            </div>

            {/* Calculation Output Box */}
            <div className="l2mid-roi-results-box">
              <div className="l2mid-roi-kpi-grid">
                <div className="l2mid-roi-kpi">
                  <span className="l2mid-kpi-title">Ahorro en Fertilizantes/Insumos</span>
                  <span className="l2mid-kpi-num">${roiResults.inputSaving} USD</span>
                  <span className="l2mid-kpi-sub">Reducción de dosis variable</span>
                </div>
                <div className="l2mid-roi-kpi">
                  <span className="l2mid-kpi-title">Ganancia por Rinde Protegido</span>
                  <span className="l2mid-kpi-num">${roiResults.extraRevenue} USD</span>
                  <span className="l2mid-kpi-sub">Detección temprana de anomalías</span>
                </div>
                <div className="l2mid-roi-kpi l2mid-roi-kpi--highlight">
                  <span className="l2mid-kpi-title">Beneficio Neto Anual Proyectado</span>
                  <span className="l2mid-kpi-num">${roiResults.netProfit} USD</span>
                  <span className="l2mid-kpi-badge">Retorno {roiResults.roiMultiplier}x sobre inversión</span>
                </div>
              </div>

              <div className="l2mid-roi-action">
                <button className="l2mid-btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={() => navigate('/login')}>
                  <span>Comenzar a optimizar mis lotes</span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── INTEGRATIONS & ECOSYSTEM MARQUEE ── */}
      <section className="l2mid-integrations-section">
        <p className="l2mid-integrations-label">ECOSISTEMA Y FORMATOS DE PRECISIÓN COMPATIBLES</p>
        <div className="l2mid-marquee-container">
          <div className="l2mid-marquee-track">
            {[...INTEGRATIONS, ...INTEGRATIONS].map((item, idx) => (
              <div key={idx} className="l2mid-marquee-pill">
                <span className="l2mid-marquee-dot" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ SECTION ── */}
      <section id="faq" className="l2mid-section l2mid-faq-section">
        <div className="l2mid-section-header">
          <div className="l2mid-section-tag">PREGUNTAS FRECUENTES</div>
          <h2 className="l2mid-section-title">Respuestas Claras para Productores y Agrónomos</h2>
          <p className="l2mid-section-desc">
            Todo lo que necesitás saber sobre la adopción de AgroNexo en tus operaciones diarias de campo.
          </p>
        </div>

        <div className="l2mid-container l2mid-container--narrow">
          <div className="l2mid-faq-accordion">
            {FAQS.map((faq, index) => (
              <div
                key={index}
                className={`l2mid-faq-card ${openFaq === index ? 'l2mid-faq-card--open' : ''}`}
                onClick={() => setOpenFaq(openFaq === index ? -1 : index)}
              >
                <div className="l2mid-faq-question-row">
                  <h3 className="l2mid-faq-question-text">{faq.q}</h3>
                  <div className="l2mid-faq-chevron">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                </div>
                {openFaq === index && (
                  <div className="l2mid-faq-answer">
                    <p>{faq.a}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FINAL CTA BANNER ── */}
      <section className="l2mid-section l2mid-cta-banner-section">
        <div className="l2mid-container l2mid-container--narrow">
          <div className="l2mid-cta-banner">
            <div className="l2mid-cta-banner-glow" />
            <div className="l2mid-cta-badge">
              <span className="l2mid-badge-pulse" />
              <span>AGRICULTURA DIGITAL EN EL NEA</span>
            </div>
            <h2 className="l2mid-cta-heading">
              Llevá tus decisiones agronómicas al siguiente nivel con AgroNexo
            </h2>
            <p className="l2mid-cta-text">
              Empezá a monitorear tus lotes con imágenes multiespectrales, detección de anomalías por IA y prescripciones listas para tu maquinaria.
            </p>
            <div className="l2mid-cta-btn-group">
              <button className="l2mid-btn-primary l2mid-btn-hero" onClick={() => navigate('/login')}>
                <span>Ingresar a la Plataforma</span>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="l2mid-footer">
        <div className="l2mid-container">
          <div className="l2mid-footer-main">
            <div className="l2mid-footer-brand-col">
              <div className="l2mid-nav-brand">
                <img src="/logo_hoja.png" alt="AgroNexo" className="l2mid-nav-logo-icon" />
                <span className="l2mid-nav-brand-text">
                  Agro<span className="l2mid-accent-text">Nexo</span>
                </span>
              </div>
              <p className="l2mid-footer-brand-desc">
                Soluciones de agricultura de precisión, procesamiento GIS y diagnóstico asistido por inteligencia artificial para el NEA argentino.
              </p>
              <div className="l2mid-footer-contact-info">
                <span>📍 Resistencia, Chaco · Argentina</span>
                <span>🛰️ EPSG:32721 · Sentinel-2 & DJI RTK</span>
              </div>
            </div>

            <div className="l2mid-footer-links-col">
              <span className="l2mid-footer-col-title">Módulos</span>
              <button className="l2mid-footer-link-btn" onClick={() => scrollToSection('demo-interactiva')}>Visor Satelital</button>
              <button className="l2mid-footer-link-btn" onClick={() => scrollToSection('comparador')}>Índices NDVI / NDRE</button>
              <button className="l2mid-footer-link-btn" onClick={() => scrollToSection('pipeline')}>Motor de Diagnóstico</button>
              <button className="l2mid-footer-link-btn" onClick={() => scrollToSection('roi-calculator')}>Prescripciones ISO-XML</button>
            </div>

            <div className="l2mid-footer-links-col">
              <span className="l2mid-footer-col-title">Plataforma</span>
              <button className="l2mid-footer-link-btn" onClick={() => navigate('/login')}>Iniciar Sesión</button>
              <button className="l2mid-footer-link-btn" onClick={() => navigate('/login')}>Crear Cuenta</button>
              <button className="l2mid-footer-link-btn" onClick={() => scrollToSection('faq')}>Preguntas Frecuentes</button>
            </div>
          </div>

          <div className="l2mid-footer-bottom">
            <span>© 2026 AgroNexo GIS Platform. Todos los derechos reservados.</span>
            <div className="l2mid-footer-bottom-links">
              <span>Términos de Servicio</span>
              <span>Privacidad Geoespacial</span>
              <span>Documentación API</span>
            </div>
          </div>
        </div>
      </footer>
    
      {/* ── 3-Version Comparison Bar ── */}
      <div style={{
        position: 'fixed',
        bottom: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 99999,
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 16px',
        borderRadius: '9999px',
        background: 'rgba(15, 23, 42, 0.94)',
        border: '1px solid rgba(255, 255, 255, 0.18)',
        boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
        backdropFilter: 'blur(16px)',
        fontSize: '12px',
        fontFamily: 'system-ui, sans-serif'
      }}>
        <span style={{ color: '#94a3b8', fontWeight: 600, marginRight: '4px' }}>Comparar:</span>
        <a href="/" style={{
          padding: '6px 12px',
          borderRadius: '9999px',
          background: 'rgba(255,255,255,0.08)',
          color: '#ffffff',
          textDecoration: 'none',
          fontWeight: 500
        }}>
          🌿 1. Nueva (Clean White) 
        </a>
        <a href="/landing-intermedia" style={{
          padding: '6px 12px',
          borderRadius: '9999px',
          background: '#27500a',
          color: '#ffffff',
          textDecoration: 'none',
          fontWeight: 700
        }}>
          🌙 2. Intermedia (Dark Pro) ✓
        </a>
        <a href="/landing-original" style={{
          padding: '6px 12px',
          borderRadius: '9999px',
          background: 'rgba(255,255,255,0.08)',
          color: '#ffffff',
          textDecoration: 'none',
          fontWeight: 500
        }}>
          📜 3. Original (Dark Glass) 
        </a>
      </div>
</div>
  )
}
