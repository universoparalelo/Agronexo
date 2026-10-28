export function etiquetaVuelo(v, { conZonas = true } = {}) {
  const fecha = new Date(v.fecha_vuelo).toLocaleDateString('es-AR', { day: '2-digit', month: 'long', year: 'numeric' })
  const partes = [fecha]
  if (v.estadio_fenologico) partes.push(v.estadio_fenologico)
  if (conZonas && v.zonas_atencion != null) {
    partes.push(v.zonas_atencion > 0
      ? `${v.zonas_atencion} zona${v.zonas_atencion === 1 ? '' : 's'} requiere${v.zonas_atencion === 1 ? '' : 'n'} atención`
      : 'sin problemas')
  }
  return partes.join(' · ')
}

// Dos vuelos del mismo día con los mismos datos darían opciones idénticas: se distinguen por la hora de subida.
export function etiquetasUnicas(vuelos, opciones) {
  const base = vuelos.map(v => etiquetaVuelo(v, opciones))
  return vuelos.map((v, i) => {
    if (base.filter(b => b === base[i]).length === 1) return base[i]
    const hora = new Date(v.created_at).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
    return `${base[i]} · subido ${hora}`
  })
}
