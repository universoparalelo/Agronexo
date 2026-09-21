import { useEffect, useRef, useCallback, useState } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import '@geoman-io/leaflet-geoman-free'
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css'
import { areaGeodesicaM2, tieneAutointerseccion } from '../utils/geometria'
import { parsearCoordenadas } from '../utils/coordenadas'

// Resistencia, Chaco — centro por defecto del mapa (foco geográfico NEA)
const CENTRO_NEA = [-27.45, -59.05]

function ControlesDibujo({ onChange, initialGeoJSON }) {
  const map = useMap()
  const capaRef = useRef(null)

  const emitir = useCallback(
    (layer) => {
      if (!layer) {
        onChange(null, null, false)
        return
      }
      const geojson = layer.toGeoJSON().geometry
      const areaM2 = areaGeodesicaM2(layer.getLatLngs()[0])
      const autointerseccion = tieneAutointerseccion(geojson.coordinates[0])
      onChange(geojson, areaM2, autointerseccion)
    },
    [onChange]
  )

  const reemplazarCapa = useCallback(
    (layer) => {
      if (capaRef.current && capaRef.current !== layer) {
        map.removeLayer(capaRef.current)
      }
      capaRef.current = layer
    },
    [map]
  )

  useEffect(() => {
    map.pm.addControls({
      position: 'topright',
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawCircle: false,
      drawText: false,
      drawRectangle: true,
      drawPolygon: true,
      editMode: true,
      dragMode: true,
      cutPolygon: false,
      removalMode: true,
      rotateMode: false,
    })

    function vincularEventosCapa(layer) {
      layer.on('pm:edit', () => emitir(layer))
      layer.on('pm:dragend', () => emitir(layer))
    }

    function onCreate(e) {
      // Un solo polígono activo por lote: la figura nueva reemplaza a la anterior.
      reemplazarCapa(e.layer)
      vincularEventosCapa(e.layer)
      emitir(e.layer)
    }

    function onRemove(e) {
      if (capaRef.current === e.layer) {
        capaRef.current = null
        emitir(null)
      }
    }

    map.on('pm:create', onCreate)
    map.on('pm:remove', onRemove)

    if (initialGeoJSON) {
      const layer = L.geoJSON(initialGeoJSON).getLayers()[0]
      layer.addTo(map)
      layer.pm.enable()
      reemplazarCapa(layer)
      vincularEventosCapa(layer)
      map.fitBounds(layer.getBounds(), { padding: [20, 20] })
      emitir(layer)
    }

    return () => {
      map.off('pm:create', onCreate)
      map.off('pm:remove', onRemove)
      map.pm.removeControls()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map])

  return null
}

const NOMINATIM = 'https://nominatim.openstreetmap.org/search'

// Buscador de lugares (Nominatim / OpenStreetMap) o coordenadas "lat, lng".
// Solo se consulta al enviar (Enter / botón): la política de uso de Nominatim
// no permite autocompletar mientras se escribe.
function BuscadorMapa() {
  const map = useMap()
  const contenedorRef = useRef(null)
  const marcadorRef = useRef(null)
  const [consulta, setConsulta] = useState('')
  const [buscando, setBuscando] = useState(false)
  const [resultados, setResultados] = useState([])
  const [mensaje, setMensaje] = useState('')

  useEffect(() => {
    // que escribir, arrastrar o hacer scroll sobre el buscador no mueva el mapa
    if (contenedorRef.current) {
      L.DomEvent.disableClickPropagation(contenedorRef.current)
      L.DomEvent.disableScrollPropagation(contenedorRef.current)
    }
    return () => { if (marcadorRef.current) map.removeLayer(marcadorRef.current) }
  }, [map])

  function marcar(lat, lng, etiqueta) {
    if (marcadorRef.current) map.removeLayer(marcadorRef.current)
    marcadorRef.current = L.circleMarker([lat, lng], {
      radius: 8, color: '#fff', weight: 2, fillColor: '#e11d48', fillOpacity: 1,
    }).addTo(map)
    if (etiqueta) marcadorRef.current.bindTooltip(etiqueta, { direction: 'top', offset: [0, -8] })
  }

  function irA(lat, lng, etiqueta, bounds) {
    marcar(lat, lng, etiqueta)
    if (bounds) map.fitBounds(bounds, { maxZoom: 17 })
    else map.flyTo([lat, lng], 16)
    setResultados([])
  }

  async function buscar(e) {
    e.preventDefault()
    const texto = consulta.trim()
    if (!texto) return
    setMensaje('')
    setResultados([])

    const coords = parsearCoordenadas(texto)
    if (coords) {
      irA(coords.lat, coords.lng, `${coords.lat.toFixed(5)}, ${coords.lng.toFixed(5)}`)
      return
    }

    setBuscando(true)
    try {
      const resp = await fetch(`${NOMINATIM}?format=jsonv2&limit=6&accept-language=es&q=${encodeURIComponent(texto)}`)
      if (!resp.ok) throw new Error(String(resp.status))
      const datos = await resp.json()
      if (datos.length === 0) setMensaje('No se encontraron resultados.')
      else if (datos.length === 1) irDesdeResultado(datos[0])
      else setResultados(datos)
    } catch {
      setMensaje('No se pudo buscar el lugar. Probá con coordenadas (lat, lng) o de nuevo en un rato.')
    } finally {
      setBuscando(false)
    }
  }

  function irDesdeResultado(r) {
    const [sur, norte, oeste, este] = (r.boundingbox ?? []).map(Number)
    const bounds = [sur, norte, oeste, este].every(Number.isFinite) ? [[sur, oeste], [norte, este]] : null
    irA(Number(r.lat), Number(r.lon), r.display_name, bounds)
    setConsulta(r.display_name.split(',')[0])
  }

  function miUbicacion() {
    setMensaje('')
    if (!navigator.geolocation) { setMensaje('Tu navegador no permite obtener la ubicación.'); return }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        marcar(pos.coords.latitude, pos.coords.longitude, 'Tu ubicación')
        map.flyTo([pos.coords.latitude, pos.coords.longitude], 17)
      },
      () => setMensaje('No se pudo obtener tu ubicación (permiso denegado o sin señal).'),
      { timeout: 10000 },
    )
  }

  return (
    <div className="mapa-buscador" ref={contenedorRef}>
      <form className="mapa-buscador-form" onSubmit={buscar} role="search">
        <input
          type="text"
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
          placeholder="Buscar lugar o lat, lng (ej: -27.45, -59.05)"
          aria-label="Buscar lugar o coordenadas"
        />
        <button type="submit" disabled={buscando || !consulta.trim()} title="Buscar">
          {buscando ? '…' : '🔍'}
        </button>
        <button type="button" onClick={miUbicacion} title="Ir a mi ubicación" aria-label="Ir a mi ubicación">📍</button>
      </form>
      {mensaje && <p className="mapa-buscador-mensaje">{mensaje}</p>}
      {resultados.length > 0 && (
        <ul className="mapa-buscador-resultados">
          {resultados.map((r) => (
            <li key={r.place_id}>
              <button type="button" onClick={() => irDesdeResultado(r)}>{r.display_name}</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function MapaDibujoLote({
  onChange,
  initialGeoJSON = null,
  center = CENTRO_NEA,
  zoom = 14,
  height = 320,
}) {
  const [mostrarReferencia, setMostrarReferencia] = useState(true)

  return (
    <div className="mapa-dibujo-wrapper">
      <button
        type="button"
        className="mapa-toggle-referencia"
        onClick={() => setMostrarReferencia((v) => !v)}
      >
        {mostrarReferencia ? '🏷️ Ocultar límites y nombres' : '🏷️ Mostrar límites y nombres'}
      </button>
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height, width: '100%', borderRadius: '8px' }}
        scrollWheelZoom
      >
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics"
          maxZoom={19}
        />
        {mostrarReferencia && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
            maxZoom={19}
            // Capa de referencia (límites político-administrativos + toponimia) sobre el
            // satelital de Esri — comparte proveedor, no agrega texto de atribución nuevo.
          />
        )}
        <ControlesDibujo onChange={onChange} initialGeoJSON={initialGeoJSON} />
        <BuscadorMapa />
      </MapContainer>
    </div>
  )
}
