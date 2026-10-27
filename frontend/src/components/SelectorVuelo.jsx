import { etiquetasUnicas } from '../utils/vuelos'

// Desplegable para cambiar de vuelo sin salir de la pantalla. `excluirId` oculta el vuelo
// que ya se está mostrando en el otro panel, para no comparar un vuelo consigo mismo.
export default function SelectorVuelo({ vuelos, valor, excluirId = null, onCambiar }) {
  const ordenados = [...vuelos].sort((a, b) => new Date(b.fecha_vuelo) - new Date(a.fecha_vuelo))
  const etiquetas = etiquetasUnicas(ordenados, { conZonas: false })

  return (
    <select
      className="selector-vuelo"
      value={valor}
      onChange={(e) => onCambiar(e.target.value)}
      aria-label="Elegir vuelo"
      title="Elegir otro vuelo del lote"
    >
      {ordenados.map((v, i) => (
        v.vuelo_id !== excluirId && <option key={v.vuelo_id} value={v.vuelo_id}>{etiquetas[i]}</option>
      ))}
    </select>
  )
}
