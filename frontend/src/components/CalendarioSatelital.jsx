import { useEffect, useState } from 'react'
import { buscarImagenesSatelitales } from '../api/analisis'

const DIAS_SEMANA = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

// Evitamos Date#toISOString() a propósito: normaliza a UTC y puede correr
// la fecha un día para atrás en husos horarios positivos — acá siempre
// leemos año/mes/día LOCALES, que es lo que el usuario ve en el calendario.
function fechaISOLocal(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function diasDelMes(date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
}

// getDay() nativo devuelve Domingo=0 — lo corremos para que la grilla
// empiece en Lunes (Lunes=0 ... Domingo=6), como el resto de la app.
function offsetInicioSemana(date) {
  return (date.getDay() + 6) % 7
}

/**
 * Selector de fecha para imágenes satelitales — reemplaza el <input
 * type="date"> nativo porque ningún navegador permite marcar días
 * puntuales dentro de su calendario emergente. Al abrirse (o cambiar de
 * mes), busca escenas Sentinel-2 en una ventana de ~20 días alrededor del
 * día 15 del mes visible y pinta de verde los días con imagen disponible
 * (ámbar si esa imagen está muy nublada) — el usuario ve de un vistazo
 * qué fechas tienen sentido elegir, en vez de adivinar y probar de a una.
 */
export default function CalendarioSatelital({ loteId, fechaSeleccionada, onSeleccionar, disabled }) {
  const [abierto, setAbierto] = useState(false)
  const [mesVisible, setMesVisible] = useState(() => {
    const hoy = new Date()
    return new Date(hoy.getFullYear(), hoy.getMonth(), 1)
  })
  const [marcas, setMarcas] = useState({}) // fecha ISO -> { nubes_pct, escena_id, ... }
  const [mesesCargados, setMesesCargados] = useState(() => new Set())
  const [cargando, setCargando] = useState(false)

  const claveMes = `${mesVisible.getFullYear()}-${mesVisible.getMonth()}`

  useEffect(() => {
    if (!abierto || !loteId || mesesCargados.has(claveMes)) return
    let cancelado = false
    setCargando(true)
    const centroDelMes = new Date(mesVisible.getFullYear(), mesVisible.getMonth(), 15)
    buscarImagenesSatelitales(loteId, fechaISOLocal(centroDelMes), 20)
      .then((data) => {
        if (cancelado) return
        setMarcas((prev) => {
          const next = { ...prev }
          for (const item of data.items) next[item.fecha] = item
          return next
        })
      })
      .catch(() => {
        // Sin escenas en este mes (todo nublado, o fuera de cobertura) —
        // no es un error para el usuario, el mes simplemente queda sin marcas.
      })
      .finally(() => {
        if (cancelado) return
        setMesesCargados((prev) => new Set(prev).add(claveMes))
        setCargando(false)
      })
    return () => { cancelado = true }
  }, [abierto, loteId, claveMes]) // eslint-disable-line react-hooks/exhaustive-deps

  function cambiarMes(delta) {
    setMesVisible((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1))
  }

  function elegirDia(dia) {
    const fecha = new Date(mesVisible.getFullYear(), mesVisible.getMonth(), dia)
    onSeleccionar(fechaISOLocal(fecha))
    setAbierto(false)
  }

  const totalDias = diasDelMes(mesVisible)
  const offset = offsetInicioSemana(new Date(mesVisible.getFullYear(), mesVisible.getMonth(), 1))
  const celdas = [...Array(offset).fill(null), ...Array.from({ length: totalDias }, (_, i) => i + 1)]

  return (
    <div className="calendario-satelital">
      <button
        type="button"
        className="calendario-satelital-trigger"
        onClick={() => setAbierto((v) => !v)}
        disabled={disabled}
      >
        {fechaSeleccionada || 'Elegí una fecha'}
        <span className="calendario-satelital-trigger-icono">📅</span>
      </button>

      {abierto && (
        <div className="calendario-satelital-popover">
          <div className="calendario-satelital-header">
            <button type="button" onClick={() => cambiarMes(-1)} aria-label="Mes anterior">‹</button>
            <span>{MESES[mesVisible.getMonth()]} {mesVisible.getFullYear()}</span>
            <button type="button" onClick={() => cambiarMes(1)} aria-label="Mes siguiente">›</button>
          </div>

          {cargando && <p className="calendario-satelital-cargando">Buscando imágenes disponibles...</p>}

          <div className="calendario-satelital-grid">
            {DIAS_SEMANA.map((d) => (
              <span key={d} className="calendario-satelital-diasemana">{d}</span>
            ))}
            {celdas.map((dia, i) => {
              if (dia == null) return <span key={`vacio-${i}`} />
              const fecha = new Date(mesVisible.getFullYear(), mesVisible.getMonth(), dia)
              const iso = fechaISOLocal(fecha)
              const marca = marcas[iso]
              const nublada = marca && marca.nubes_pct != null && marca.nubes_pct > 30
              const clases = ['calendario-satelital-dia']
              if (marca) clases.push(nublada ? 'calendario-satelital-dia--nublado' : 'calendario-satelital-dia--disponible')
              if (iso === fechaSeleccionada) clases.push('calendario-satelital-dia--activo')
              return (
                <button
                  type="button"
                  key={iso}
                  className={clases.join(' ')}
                  title={marca ? `${marca.nubes_pct != null ? marca.nubes_pct.toFixed(1) : '?'}% de nubes` : 'Sin escena Sentinel-2 conocida para este día'}
                  onClick={() => elegirDia(dia)}
                >
                  {dia}
                </button>
              )
            })}
          </div>

          <div className="calendario-satelital-leyenda">
            <span><i className="calendario-satelital-punto calendario-satelital-punto--disponible" /> Imagen disponible</span>
            <span><i className="calendario-satelital-punto calendario-satelital-punto--nublado" /> Muy nublada</span>
          </div>
        </div>
      )}
    </div>
  )
}
