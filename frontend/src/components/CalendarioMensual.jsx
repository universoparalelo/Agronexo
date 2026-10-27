import { useState } from 'react'
import { fechaISOLocal, fechaVuelo } from '../utils/fechas'

const DIAS_SEMANA = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

const SENSOR_LABELS = { sentinel2: 'Sentinel-2', dji_mavic3: 'DJI Mavic 3' }
const ESTADO_LABELS = { pendiente: 'Pendiente', procesando: 'Procesando', completado: 'Completado', error: 'Error' }

function diasDelMes(date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
}

function offsetInicioSemana(date) {
  return (date.getDay() + 6) % 7
}

function idDe(vuelo) {
  return vuelo.vuelo_id ?? vuelo.id
}

/**
 * Solo la grilla del calendario (navegación mes/año + días + leyenda) —
 * sin título ni lista de vuelos del día, para poder ubicarla donde haga
 * falta (al lado de una lista propia, dentro de un drawer, etc.). El día
 * elegido es estado del padre; la navegación de mes/año es interna.
 */
export default function CalendarioMensual({ vuelos, vueloActualId, diaSeleccionado, onSeleccionarDia }) {
  const vueloActual = vuelos.find(v => idDe(v) === vueloActualId)
  const fechaInicial = diaSeleccionado
    ? new Date(`${diaSeleccionado}T00:00:00`)
    : vueloActual ? fechaVuelo(vueloActual.fecha_vuelo) : new Date()

  const [mesVisible, setMesVisible] = useState(
    () => new Date(fechaInicial.getFullYear(), fechaInicial.getMonth(), 1)
  )
  const [vista, setVista] = useState('mes') // 'mes' | 'anio'

  const porFecha = {}
  for (const v of vuelos) {
    const iso = fechaISOLocal(fechaVuelo(v.fecha_vuelo))
    ;(porFecha[iso] ??= []).push(v)
  }

  function cambiarMes(delta) {
    setMesVisible(prev => new Date(prev.getFullYear(), prev.getMonth() + delta, 1))
  }

  function cambiarAnio(delta) {
    setMesVisible(prev => new Date(prev.getFullYear() + delta, prev.getMonth(), 1))
  }

  function elegirMes(indiceMes) {
    setMesVisible(prev => new Date(prev.getFullYear(), indiceMes, 1))
    setVista('mes')
  }

  const totalDias = diasDelMes(mesVisible)
  const offset = offsetInicioSemana(new Date(mesVisible.getFullYear(), mesVisible.getMonth(), 1))
  const celdas = [...Array(offset).fill(null), ...Array.from({ length: totalDias }, (_, i) => i + 1)]

  const mesesConVueloDelAnio = new Set(
    vuelos
      .map(v => fechaVuelo(v.fecha_vuelo))
      .filter(f => f.getFullYear() === mesVisible.getFullYear())
      .map(f => f.getMonth())
  )

  return (
    <div className="calendario-mensual">
      {vista === 'mes' ? (
        <div className="vuelos-calendario-header">
          <button type="button" onClick={() => cambiarMes(-1)} aria-label="Mes anterior">‹</button>
          <button
            type="button"
            className="vuelos-calendario-anio-boton"
            onClick={() => setVista('anio')}
            title="Ver los meses del año"
          >
            {MESES[mesVisible.getMonth()]} {mesVisible.getFullYear()}
          </button>
          <button type="button" onClick={() => cambiarMes(1)} aria-label="Mes siguiente">›</button>
        </div>
      ) : (
        <div className="vuelos-calendario-header">
          <button type="button" onClick={() => cambiarAnio(-1)} aria-label="Año anterior">‹</button>
          <span>{mesVisible.getFullYear()}</span>
          <button type="button" onClick={() => cambiarAnio(1)} aria-label="Año siguiente">›</button>
        </div>
      )}

      {vista === 'anio' && (
        <div className="vuelos-calendario-meses-grid">
          {MESES.map((mes, i) => {
            const tieneVuelo = mesesConVueloDelAnio.has(i)
            const esVisible = i === mesVisible.getMonth()
            const clases = ['vuelos-calendario-mes-celda']
            if (tieneVuelo) clases.push('vuelos-calendario-mes-celda--con-vuelo')
            if (esVisible) clases.push('vuelos-calendario-mes-celda--activo')
            return (
              <button type="button" key={mes} className={clases.join(' ')} onClick={() => elegirMes(i)}>
                {mes.slice(0, 3)}
              </button>
            )
          })}
        </div>
      )}

      {vista === 'mes' && (
        <>
          <div className="vuelos-calendario-grid">
            {DIAS_SEMANA.map(d => (
              <span key={d} className="vuelos-calendario-diasemana">{d}</span>
            ))}
            {celdas.map((dia, i) => {
              if (dia == null) return <span key={`vacio-${i}`} />
              const fecha = new Date(mesVisible.getFullYear(), mesVisible.getMonth(), dia)
              const iso = fechaISOLocal(fecha)
              const vuelosDelDia = porFecha[iso] || []
              const tieneVuelo = vuelosDelDia.length > 0
              const esActual = vuelosDelDia.some(v => idDe(v) === vueloActualId)
              const esSeleccionado = iso === diaSeleccionado
              const clases = ['vuelos-calendario-dia']
              if (tieneVuelo) clases.push('vuelos-calendario-dia--con-vuelo')
              if (esActual) clases.push('vuelos-calendario-dia--activo')
              if (esSeleccionado) clases.push('vuelos-calendario-dia--seleccionado')

              const titulo = tieneVuelo
                ? vuelosDelDia
                    .map(v => `${SENSOR_LABELS[v.sensor] || v.sensor} · ${ESTADO_LABELS[v.estado] || v.estado}`)
                    .join(' / ')
                : undefined

              return (
                <button
                  type="button"
                  key={iso}
                  className={clases.join(' ')}
                  title={titulo}
                  onClick={() => onSeleccionarDia(iso)}
                >
                  {dia}
                  {vuelosDelDia.length > 1 && <span className="vuelos-calendario-contador">{vuelosDelDia.length}</span>}
                </button>
              )
            })}
          </div>
        </>
      )}

      <div className="vuelos-calendario-leyenda">
        <span><i className="vuelos-calendario-punto vuelos-calendario-punto--con-vuelo" /> Con vuelo</span>
      </div>
    </div>
  )
}
