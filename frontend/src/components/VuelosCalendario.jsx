import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import CalendarioMensual from './CalendarioMensual'
import { fechaISOLocal, fechaDDMMAAAA } from '../utils/fechas'

const SENSOR_LABELS = { sentinel2: 'Sentinel-2', dji_mavic3: 'DJI Mavic 3' }
const ESTADO_LABELS = { pendiente: 'Pendiente', procesando: 'Procesando', completado: 'Completado', error: 'Error' }

function idDe(vuelo) {
  return vuelo.vuelo_id ?? vuelo.id
}

/**
 * Calendario de solo lectura con todos los vuelos del lote — se muestra al
 * lado del panel de diagnóstico para ubicar en el tiempo el análisis actual
 * respecto de los demás. Arranca en el día del vuelo que se está mirando.
 */
export default function VuelosCalendario({ loteId, vuelos, vueloActualId, onCerrar, onComparar, onNuevoAnalisis }) {
  const navigate = useNavigate()

  const vueloActual = vuelos.find(v => idDe(v) === vueloActualId)
  const fechaInicial = vueloActual ? new Date(vueloActual.fecha_vuelo) : new Date()
  const [diaSeleccionado, setDiaSeleccionado] = useState(() => fechaISOLocal(fechaInicial))
  const [menuAbiertoId, setMenuAbiertoId] = useState(null)

  useEffect(() => {
    if (!menuAbiertoId) return
    const cerrar = () => setMenuAbiertoId(null)
    window.addEventListener('click', cerrar)
    return () => window.removeEventListener('click', cerrar)
  }, [menuAbiertoId])

  const porFecha = {}
  for (const v of vuelos) {
    const iso = fechaISOLocal(new Date(v.fecha_vuelo))
    ;(porFecha[iso] ??= []).push(v)
  }

  function irAVuelo(destino) {
    if (idDe(destino) !== vueloActualId) navigate(`/lotes/${loteId}/vuelos/${idDe(destino)}`)
  }

  const vuelosDelDiaSeleccionado = (porFecha[diaSeleccionado] || [])
    .slice()
    .sort((a, b) => new Date(b.fecha_vuelo) - new Date(a.fecha_vuelo))

  return (
    <div className="vuelos-calendario">
      <div className="vuelos-calendario-titulo-fila">
        <h3 className="vuelos-calendario-titulo">Vuelos del lote</h3>
        <button
          type="button"
          className="vuelos-calendario-cerrar"
          onClick={onCerrar}
          aria-label="Cerrar calendario de vuelos"
          title="Cerrar"
        >
          ×
        </button>
      </div>

      <CalendarioMensual
        vuelos={vuelos}
        vueloActualId={vueloActualId}
        diaSeleccionado={diaSeleccionado}
        onSeleccionarDia={setDiaSeleccionado}
      />

      <div className="vuelos-calendario-lista">
        <div className="vuelos-calendario-lista-titulo-fila">
          <h4 className="vuelos-calendario-lista-titulo">Vuelos del {fechaDDMMAAAA(diaSeleccionado)}</h4>
          {onNuevoAnalisis && (
            <button type="button" className="vuelos-calendario-nuevo-analisis" onClick={onNuevoAnalisis}>
              ＋ Cargar nuevo análisis
            </button>
          )}
        </div>
        {vuelosDelDiaSeleccionado.length === 0 && (
          <p className="empty-hint">Sin vuelos cargados ese día.</p>
        )}
        <ul>
          {vuelosDelDiaSeleccionado.map(v => {
            const esActual = idDe(v) === vueloActualId
            const seleccionable = v.estado === 'completado'
            const puedeComparar = onComparar && !esActual && seleccionable
            return (
              <li key={idDe(v)} className="vuelos-calendario-item-fila">
                <button
                  type="button"
                  className={`vuelos-calendario-item ${esActual ? 'vuelos-calendario-item--activo' : ''}`}
                  disabled={!seleccionable}
                  title={seleccionable ? undefined : 'Este vuelo todavía no tiene resultados para ver'}
                  onClick={() => seleccionable && irAVuelo(v)}
                >
                  <span className="vuelos-calendario-item-sensor">{SENSOR_LABELS[v.sensor] || v.sensor}</span>
                  <span className={`estado-badge estado-${v.estado}`}>{ESTADO_LABELS[v.estado] || v.estado}</span>
                </button>
                {puedeComparar && (
                  <div className="vuelos-calendario-item-menu">
                    <button
                      type="button"
                      className="vuelos-calendario-item-menu-boton"
                      onClick={(e) => { e.stopPropagation(); setMenuAbiertoId(prev => prev === idDe(v) ? null : idDe(v)) }}
                      aria-label="Más opciones"
                      title="Más opciones"
                    >
                      ⋮
                    </button>
                    {menuAbiertoId === idDe(v) && (
                      <div className="vuelos-calendario-item-menu-lista">
                        <button type="button" onClick={() => { onComparar(v); setMenuAbiertoId(null) }}>
                          Seleccionar para comparar
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
