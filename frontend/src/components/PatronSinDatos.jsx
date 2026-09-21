// Definición (oculta) del rayado que marca "sin datos" en los mapas. Un SVG
// 0×0 y no display:none: varios navegadores no resuelven fill="url(#…)" si el
// <defs> está en un elemento sin renderizar. La clase .capa-sin-datos (index.css)
// lo aplica a las capas de Leaflet.
export default function PatronSinDatos() {
  return (
    <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true" focusable="false">
      <defs>
        <pattern id="patron-sin-datos" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="8" height="8" fill="#f3f4f6" />
          <line x1="0" y1="0" x2="0" y2="8" stroke="#6b7280" strokeWidth="2.5" />
        </pattern>
      </defs>
    </svg>
  )
}

export const ESTILO_SIN_DATOS = { className: 'capa-sin-datos', weight: 1.5, color: '#4b5563', dashArray: '4 3', fillOpacity: 1 }

export const TEXTO_SIN_DATOS = 'Sin datos: no hay información de este análisis en esta parte del lote.'
