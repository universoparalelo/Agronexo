// Evitamos Date#toISOString() a propósito: normaliza a UTC y puede correr la
// fecha un día para atrás en husos horarios positivos — acá siempre leemos
// año/mes/día LOCALES, que es lo que el usuario ve en el calendario.
export function fechaISOLocal(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function fechaDDMMAAAA(iso) {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}
