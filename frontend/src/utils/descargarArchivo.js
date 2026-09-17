// Dispara la descarga de un Blob en el navegador — no hay ningún <a> real
// apuntando al archivo (viene del body de la respuesta, no de una URL
// pública), así que se arma un link sintético descartable.
export function descargarBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// Con responseType:'blob' en axios, un error HTTP (404/500) también llega
// como Blob en vez de JSON — sin esto, el mensaje de error mostrado sería
// literalmente "[object Blob]" en vez del detail real del backend.
export async function extraerMensajeErrorBlob(err, fallback) {
  const data = err?.response?.data
  if (data instanceof Blob) {
    try {
      const texto = await data.text()
      const json = JSON.parse(texto)
      return json.detail || fallback
    } catch {
      return fallback
    }
  }
  return err?.response?.data?.detail || fallback
}
