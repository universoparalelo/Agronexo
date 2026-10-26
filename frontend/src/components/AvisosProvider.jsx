import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

const AvisosContext = createContext({ avisar: () => {} })

const DURACION_MS = 4000
const DESVANECER_MS = 500

export function AvisosProvider({ children }) {
  const [avisos, setAvisos] = useState([])
  const siguienteId = useRef(0)
  const temporizadores = useRef(new Set())

  const programar = useCallback((fn, ms) => {
    const t = setTimeout(() => { temporizadores.current.delete(t); fn() }, ms)
    temporizadores.current.add(t)
  }, [])

  // Primero se marca como "saliendo" para que el CSS lo desvanezca; recién después se quita.
  const cerrar = useCallback((id) => {
    setAvisos((lista) => lista.map((a) => (a.id === id ? { ...a, saliendo: true } : a)))
    programar(() => setAvisos((lista) => lista.filter((a) => a.id !== id)), DESVANECER_MS)
  }, [programar])

  const avisar = useCallback((texto) => {
    const id = siguienteId.current++
    setAvisos((lista) => [...lista, { id, texto, saliendo: false }])
    programar(() => cerrar(id), DURACION_MS)
  }, [programar, cerrar])

  useEffect(() => {
    const activos = temporizadores.current
    return () => activos.forEach((t) => clearTimeout(t))
  }, [])

  return (
    <AvisosContext.Provider value={{ avisar }}>
      {children}
      <div className="avisos" role="status" aria-live="polite">
        {avisos.map((a) => (
          <div key={a.id} className={`aviso${a.saliendo ? ' aviso--saliendo' : ''}`}>
            <span className="aviso-icono" aria-hidden="true">✓</span>
            <span className="aviso-texto">{a.texto}</span>
            <button type="button" className="aviso-cerrar" onClick={() => cerrar(a.id)} aria-label="Cerrar aviso">✕</button>
          </div>
        ))}
      </div>
    </AvisosContext.Provider>
  )
}

export function useAvisos() {
  return useContext(AvisosContext)
}
