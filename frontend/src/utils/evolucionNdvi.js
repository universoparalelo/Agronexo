// Forma narrativa (no la corta de las tablas) — mismo texto que
// app/diagnostico/texto.py::CAUSA_LABELS, más "suelo_desnudo" para R01.
const CAUSA_TEXTO = {
  suelo_desnudo: 'zonas sin plantas (suelo desnudo o falla de siembra)',
  interferencia_vegetacion: 'interferencia de malezas',
  estres_biotico_fungico: 'enfermedad fúngica probable',
  estres_biotico_insecto: 'ataque de insectos probable',
  estres_nutricional_nitrogeno: 'déficit de nitrógeno',
  estres_nutricional_micro: 'déficit de micronutrientes (Mg/B)',
  estres_nutricional_fosforo: 'déficit de fósforo',
  estres_hidrico: 'estrés hídrico',
  madurez_temprana_diferencial: 'madurez temprana diferencial',
  vigor_excesivo: 'vigor excesivo',
  compactacion_falla_siembra: 'compactación o falla de siembra',
  bajo_vigor_estadio: 'vigor bajo para el estadio sin causa puntual',
}

// fecha_vuelo se carga como fecha sin hora (medianoche UTC): formatear en
// UTC para que en Argentina (UTC-3) no se muestre el día anterior.
export function fechaVueloCorta(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', timeZone: 'UTC' })
}

export function estadoVsEsperado(punto) {
  if (!punto.esperado) return null
  if (punto.ndviProm < punto.esperado.min) return 'debajo'
  if (punto.ndviProm > punto.esperado.max) return 'encima'
  return 'normal'
}

function plural(n, singular, pluralTxt) {
  return n === 1 ? singular : pluralTxt
}

function causasDetalle(puntos) {
  const total = {}
  for (const p of puntos) {
    for (const [causa, area] of Object.entries(p.causas || {})) {
      total[causa] = (total[causa] || 0) + area
    }
  }
  return Object.entries(total)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([causa, area]) => ({ texto: CAUSA_TEXTO[causa] || causa, area }))
}

function causasPrincipales(puntos) {
  return causasDetalle(puntos).map(c => `${c.texto} (${c.area.toFixed(1)} ha)`)
}

// Los mismos datos que cuenta explicarEvolucion, pero estructurados para
// mostrarlos como tarjetas en vez de párrafos. Null si ningún vuelo es comparable.
export function resumirEvolucion(puntos) {
  const comparables = puntos.filter(p => p.esperado)
  if (comparables.length === 0) return null

  const estados = comparables.map(estadoVsEsperado)
  const ultimo = comparables[comparables.length - 1]
  const diff = ultimo.ndviProm - ultimo.esperado.valor

  let tendencia = null
  if (comparables.length >= 2) {
    const primero = comparables[0]
    const brechaInicial = Math.abs(primero.ndviProm - primero.esperado.valor)
    const brechaFinal = Math.abs(diff)
    if (brechaFinal < brechaInicial - 0.03) tendencia = 'achica'
    else if (brechaFinal > brechaInicial + 0.03) tendencia = 'agranda'
  }

  const vuelosDebajo = comparables.filter(p => estadoVsEsperado(p) === 'debajo')
  const aRevisar = vuelosDebajo.length > 0
    ? { tipo: 'debajo', causas: causasDetalle(vuelosDebajo) }
    : { tipo: 'zonas', causas: causasDetalle([puntos[puntos.length - 1]]) }

  return {
    total: comparables.length,
    enRango: estados.filter(e => e === 'normal').length,
    debajo: estados.filter(e => e === 'debajo').length,
    encima: estados.filter(e => e === 'encima').length,
    ultimo: {
      fecha: ultimo.fecha,
      estadio: ultimo.estadio,
      ndvi: ultimo.ndviProm,
      esperado: ultimo.esperado.valor,
      diff,
      estado: estadoVsEsperado(ultimo),
      tendencia,
    },
    aRevisar,
  }
}

// Explicación general, en lenguaje simple, de la diferencia entre el NDVI
// real del lote y el esperado para cada etapa, apoyada en las causas que
// detectó el diagnóstico de cada vuelo. Devuelve una lista de párrafos.
export function explicarEvolucion(puntos) {
  const comparables = puntos.filter(p => p.esperado)
  if (comparables.length === 0) {
    return [
      'No se puede comparar con el NDVI normal del cultivo: ningún vuelo tiene un estadio fenológico ' +
      'que coincida con la curva de referencia (por ejemplo V4, R3). Cargá el estadio al subir el vuelo.',
    ]
  }

  const parrafos = []
  const estados = comparables.map(estadoVsEsperado)
  const nNormal = estados.filter(e => e === 'normal').length
  const nDebajo = estados.filter(e => e === 'debajo').length
  const nEncima = estados.filter(e => e === 'encima').length
  const n = comparables.length

  let general = `En ${nNormal} de ${n} ${plural(n, 'vuelo', 'vuelos')} el lote estuvo dentro del rango normal para su etapa`
  if (nDebajo) general += `; en ${nDebajo} quedó por debajo`
  if (nEncima) general += `; en ${nEncima} quedó por encima`
  parrafos.push(`${general}.`)

  const ultimo = comparables[comparables.length - 1]
  const diff = ultimo.ndviProm - ultimo.esperado.valor
  const estadoUltimo = estadoVsEsperado(ultimo)
  const comoEsta = estadoUltimo === 'normal'
    ? 'dentro de lo normal'
    : `${Math.abs(diff).toFixed(2)} ${diff < 0 ? 'por debajo' : 'por encima'} de lo esperado`
  let textoUltimo = `En el último vuelo comparable (${fechaVueloCorta(ultimo.fecha)}, estadio ${ultimo.estadio}) ` +
    `el NDVI fue ${ultimo.ndviProm.toFixed(2)} contra ${ultimo.esperado.valor.toFixed(2)} esperado: ${comoEsta}.`
  if (comparables.length >= 2) {
    const primero = comparables[0]
    const brechaInicial = Math.abs(primero.ndviProm - primero.esperado.valor)
    const brechaFinal = Math.abs(diff)
    if (brechaFinal < brechaInicial - 0.03) textoUltimo += ' La diferencia con lo normal se viene achicando.'
    else if (brechaFinal > brechaInicial + 0.03) textoUltimo += ' La diferencia con lo normal se viene agrandando.'
  }
  parrafos.push(textoUltimo)

  const vuelosDebajo = comparables.filter(p => estadoVsEsperado(p) === 'debajo')
  if (vuelosDebajo.length > 0) {
    const causas = causasPrincipales(vuelosDebajo)
    parrafos.push(causas.length > 0
      ? `Según los diagnósticos de los vuelos por debajo de lo normal, lo que más explica la diferencia es: ${causas.join(', ')}.`
      : 'Los diagnósticos de esos vuelos no encontraron una causa puntual por zona: la caída es pareja en todo ' +
        'el lote, lo que suele responder a factores generales (clima, fecha de siembra, suelo).')
  } else {
    const causas = causasPrincipales([puntos[puntos.length - 1]])
    if (causas.length > 0) {
      parrafos.push(`Aunque el promedio del lote está en rango, el último diagnóstico marca zonas a revisar: ${causas.join(', ')}.`)
    }
  }

  return parrafos
}
