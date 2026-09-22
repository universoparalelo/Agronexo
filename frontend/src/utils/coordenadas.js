// Interpreta lo que el usuario escribe en el buscador del mapa como un par
// latitud/longitud en grados decimales. Acepta:
//   -27.45, -59.05      -27.45 -59.05      -27.45;-59.05
//   27.45 S, 59.05 W    27.45°S 59.05°O
// El orden es siempre latitud primero. Devuelve { lat, lng } o null si no
// parece un par de coordenadas (en cuyo caso se busca como nombre de lugar).
const PATRON = /^\s*([+-]?\d{1,3}(?:[.,]\d+)?)\s*°?\s*([NSns])?\s*(?:[;,]|\s)\s*([+-]?\d{1,3}(?:[.,]\d+)?)\s*°?\s*([EWOewo])?\s*$/

export function parsearCoordenadas(texto) {
  const m = PATRON.exec(texto ?? '')
  if (!m) return null
  let lat = parseFloat(m[1].replace(',', '.'))
  let lng = parseFloat(m[3].replace(',', '.'))
  if (m[2] && /s/i.test(m[2])) lat = -Math.abs(lat)
  if (m[4] && /[wo]/i.test(m[4])) lng = -Math.abs(lng)
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return null
  return { lat, lng }
}
