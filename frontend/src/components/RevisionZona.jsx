import { useState } from 'react'
import { borrarRevisionZona, revisarZonaDiagnostico } from '../api/analisis'

// Clases del motor probabilístico (app/diagnostico/bayes.py::CAUSAS) — son
// las causas que el agrónomo puede confirmar al modificar un diagnóstico.
export const CAUSAS_REVISABLES = {
  sin_problema_detectado: 'Sin problema',
  suelo_desnudo: 'Suelo desnudo / falla de implantación',
  interferencia_vegetacion: 'Malezas',
  estres_biotico_fungico: 'Enfermedad fúngica',
  estres_biotico_insecto: 'Insectos',
  estres_nutricional_nitrogeno: 'Déficit de nitrógeno',
  estres_nutricional_micro: 'Déficit de micronutrientes',
  estres_nutricional_fosforo: 'Déficit de fósforo',
  estres_hidrico: 'Estrés hídrico',
  compactacion_falla_siembra: 'Compactación / falla de siembra',
  madurez_temprana_diferencial: 'Madurez temprana diferencial',
  vigor_excesivo: 'Vigor excesivo',
}

const DECISION_LABELS = {
  aceptado: 'Aceptado',
  modificado: 'Modificado',
  rechazado: 'Rechazado',
}

// Criterio técnico del agrónomo sobre el diagnóstico de UNA zona (RFDR-04).
// Cada revisión con causa queda como caso etiquetado del motor probabilístico.
export default function RevisionZona({ loteId, vueloId, zonaId, causaSugerida, revision, bayes, onCambio }) {
  const [modo, setModo] = useState(null)
  const [causa, setCausa] = useState('')
  const [comentario, setComentario] = useState(revision?.comentario || '')
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')

  async function guardar(decision) {
    setGuardando(true)
    setError('')
    try {
      const body = { decision, comentario: comentario || null }
      if (decision !== 'aceptado' && causa) body.causa_confirmada = causa
      const nueva = await revisarZonaDiagnostico(loteId, vueloId, zonaId, body)
      onCambio(zonaId, nueva)
      setModo(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'No se pudo guardar la revisión.')
    } finally {
      setGuardando(false)
    }
  }

  async function deshacer() {
    setGuardando(true)
    setError('')
    try {
      await borrarRevisionZona(loteId, vueloId, zonaId)
      onCambio(zonaId, null)
      setComentario('')
    } catch (err) {
      setError(err.response?.data?.detail || 'No se pudo quitar la revisión.')
    } finally {
      setGuardando(false)
    }
  }

  if (revision && modo === null) {
    return (
      <div className={`revision-zona revision-zona--${revision.decision}`}>
        <span className="revision-zona-titulo">Criterio técnico: <strong>{DECISION_LABELS[revision.decision]}</strong></span>
        {revision.causa_confirmada && (
          <span> · causa real: {CAUSAS_REVISABLES[revision.causa_confirmada] || revision.causa_confirmada}</span>
        )}
        {revision.comentario && <p className="revision-zona-comentario">“{revision.comentario}”</p>}
        <div className="revision-zona-acciones">
          <button type="button" className="revision-btn" onClick={() => { setModo('editar'); setCausa(revision.causa_confirmada || '') }} disabled={guardando}>Cambiar</button>
          <button type="button" className="revision-btn" onClick={deshacer} disabled={guardando}>Quitar</button>
        </div>
        {error && <p className="revision-zona-error">{error}</p>}
      </div>
    )
  }

  // Primero las causas que el motor probabilístico considera posibles, con su
  // porcentaje; el resto queda abajo para no tener que recorrer la lista.
  const posterior = bayes?.posterior || {}
  const opciones = Object.entries(CAUSAS_REVISABLES)
    .filter(([k]) => k !== causaSugerida)
    .sort(([a], [b]) => (posterior[b] || 0) - (posterior[a] || 0))
  const probables = opciones.filter(([k]) => (posterior[k] || 0) >= 0.05).slice(0, 4)
  const otras = opciones.filter(([k]) => !probables.some(([p]) => p === k))

  return (
    <div className="revision-zona">
      <span className="revision-zona-titulo">Criterio técnico (RFDR-04)</span>
      <div className="revision-zona-acciones">
        <button type="button" className="revision-btn revision-btn--ok" onClick={() => guardar('aceptado')} disabled={guardando}>
          ✓ Aceptar
        </button>
        <button type="button" className={`revision-btn ${modo === 'modificar' ? 'revision-btn--activo' : ''}`} onClick={() => setModo(modo === 'modificar' ? null : 'modificar')} disabled={guardando}>
          ✎ Modificar
        </button>
        <button type="button" className={`revision-btn ${modo === 'rechazar' ? 'revision-btn--activo' : ''}`} onClick={() => setModo(modo === 'rechazar' ? null : 'rechazar')} disabled={guardando}>
          ✕ Rechazar
        </button>
      </div>

      {(modo === 'modificar' || modo === 'rechazar' || modo === 'editar') && (
        <div className="revision-zona-form">
          <label>
            {modo === 'modificar' ? 'Causa confirmada a campo' : 'Causa real (opcional)'}
            <select value={causa} onChange={(e) => setCausa(e.target.value)}>
              <option value="">{modo === 'modificar' ? 'Elegir…' : 'No sé / no aplica'}</option>
              {probables.length > 0 && (
                <optgroup label="Más probables según el motor">
                  {probables.map(([k, label]) => (
                    <option key={k} value={k}>{label} ({Math.round(posterior[k] * 100)}%)</option>
                  ))}
                </optgroup>
              )}
              <optgroup label={probables.length > 0 ? 'Otras causas' : 'Causas'}>
                {otras.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </optgroup>
            </select>
          </label>
          <label>
            Comentario
            <textarea rows={2} value={comentario} onChange={(e) => setComentario(e.target.value)} placeholder="Qué se vio en el campo" />
          </label>
          <div className="revision-zona-acciones">
            {modo === 'editar' ? (
              <>
                <button type="button" className="revision-btn revision-btn--ok" onClick={() => guardar(causa ? 'modificado' : 'aceptado')} disabled={guardando}>Guardar</button>
                <button type="button" className="revision-btn" onClick={() => guardar('rechazado')} disabled={guardando}>Marcar como rechazado</button>
              </>
            ) : (
              <button
                type="button"
                className="revision-btn revision-btn--ok"
                onClick={() => guardar(modo === 'modificar' ? 'modificado' : 'rechazado')}
                disabled={guardando || (modo === 'modificar' && !causa)}
              >
                Guardar
              </button>
            )}
            <button type="button" className="revision-btn" onClick={() => setModo(null)} disabled={guardando}>Cancelar</button>
          </div>
        </div>
      )}
      {error && <p className="revision-zona-error">{error}</p>}
    </div>
  )
}
