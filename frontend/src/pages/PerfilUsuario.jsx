import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import PanelLayout from '../components/PanelLayout'
import {
  actualizarPerfil,
  cambiarPassword,
  subirAvatar,
  subirLogoEmpresa,
} from '../api/perfil'
import { listarProductosFitosanitarios } from '../api/productos'

function datosFormDesdeUsuario(u) {
  return {
    nombre: u?.nombre ?? '',
    descripcion: u?.descripcion ?? '',
    cuit: u?.cuit ?? '',
    telefono_contacto: u?.telefono_contacto ?? '',
    matricula_aplicador: u?.matricula_aplicador ?? '',
    nombre_empresa: u?.nombre_empresa ?? '',
  }
}

// Mismo catálogo que ModalCargaGeoTIFF.jsx/Dashboard.jsx — los 5 índices
// que el worker GIS calcula (workers/gis/band_mapping.py).
const INDICES_PREFERIDOS = [
  { value: 'ndvi', label: 'NDVI' },
  { value: 'ndre', label: 'NDRE' },
  { value: 'savi', label: 'SAVI' },
  { value: 'gndvi', label: 'GNDVI' },
  { value: 'exg', label: 'ExG' },
]

const UNIDADES_AREA = [
  { value: 'ha', label: 'Hectáreas (ha)' },
  { value: 'acre', label: 'Acres' },
]

function preferenciasDesdeUsuario(u) {
  return {
    indice_preferido: u?.indice_preferido ?? '',
    unidad_area_preferida: u?.unidad_area_preferida ?? '',
    producto_habitual_id: u?.producto_habitual_id ?? '',
  }
}

function mensajeError(err, fallback) {
  const detail = err.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ')
  return fallback
}

export default function PerfilUsuario() {
  const { user, actualizarUsuario } = useAuth()
  const [form, setForm] = useState(() => datosFormDesdeUsuario(user))
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')

  const [subiendoAvatar, setSubiendoAvatar] = useState(false)
  const [subiendoLogo, setSubiendoLogo] = useState(false)
  const avatarInputRef = useRef(null)
  const logoInputRef = useRef(null)

  const [passActual, setPassActual] = useState('')
  const [passNueva, setPassNueva] = useState('')
  const [passConfirmar, setPassConfirmar] = useState('')
  const [cambiandoPass, setCambiandoPass] = useState(false)
  const [errorPass, setErrorPass] = useState('')
  const [okPass, setOkPass] = useState('')

  const [preferencias, setPreferencias] = useState(() => preferenciasDesdeUsuario(user))
  const [guardandoPreferencias, setGuardandoPreferencias] = useState(false)
  const [errorPreferencias, setErrorPreferencias] = useState('')
  const [okPreferencias, setOkPreferencias] = useState('')
  const [productos, setProductos] = useState([])

  useEffect(() => {
    listarProductosFitosanitarios()
      .then((data) => setProductos(data.items ?? []))
      .catch(() => setProductos([]))
  }, [])

  function setCampo(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }))
  }

  function setCampoPreferencia(campo, valor) {
    setPreferencias((p) => ({ ...p, [campo]: valor }))
  }

  async function handleGuardarPreferencias(e) {
    e.preventDefault()
    setGuardandoPreferencias(true)
    setErrorPreferencias('')
    setOkPreferencias('')
    try {
      const usuario = await actualizarPerfil({
        indice_preferido: preferencias.indice_preferido || null,
        unidad_area_preferida: preferencias.unidad_area_preferida || null,
        producto_habitual_id: preferencias.producto_habitual_id || null,
      })
      actualizarUsuario(usuario)
      setOkPreferencias('Preferencias actualizadas correctamente.')
    } catch (err) {
      setErrorPreferencias(mensajeError(err, 'No se pudieron guardar las preferencias. Intentá de nuevo.'))
    } finally {
      setGuardandoPreferencias(false)
    }
  }

  async function handleGuardar(e) {
    e.preventDefault()
    if (!form.nombre.trim()) { setError('El nombre no puede estar vacío.'); return }
    setGuardando(true)
    setError('')
    setOk('')
    try {
      const usuario = await actualizarPerfil({
        nombre: form.nombre.trim(),
        descripcion: form.descripcion.trim() || null,
        cuit: form.cuit.trim() || null,
        telefono_contacto: form.telefono_contacto.trim() || null,
        matricula_aplicador: form.matricula_aplicador.trim() || null,
        nombre_empresa: form.nombre_empresa.trim() || null,
      })
      actualizarUsuario(usuario)
      setOk('Perfil actualizado correctamente.')
    } catch (err) {
      setError(mensajeError(err, 'No se pudo actualizar el perfil. Verificá los datos e intentá de nuevo.'))
    } finally {
      setGuardando(false)
    }
  }

  async function handleAvatar(archivo) {
    if (!archivo) return
    setSubiendoAvatar(true)
    setError('')
    try {
      const usuario = await subirAvatar(archivo)
      actualizarUsuario(usuario)
    } catch (err) {
      setError(mensajeError(err, 'No se pudo subir el avatar. Probá con una imagen JPG o PNG.'))
    } finally {
      setSubiendoAvatar(false)
    }
  }

  async function handleLogo(archivo) {
    if (!archivo) return
    setSubiendoLogo(true)
    setError('')
    try {
      const usuario = await subirLogoEmpresa(archivo)
      actualizarUsuario(usuario)
    } catch (err) {
      setError(mensajeError(err, 'No se pudo subir el logo. Probá con una imagen JPG o PNG.'))
    } finally {
      setSubiendoLogo(false)
    }
  }

  async function handleCambiarPassword(e) {
    e.preventDefault()
    setErrorPass('')
    setOkPass('')
    if (passNueva.length < 8) { setErrorPass('La contraseña nueva debe tener al menos 8 caracteres.'); return }
    if (passNueva !== passConfirmar) { setErrorPass('Las contraseñas nuevas no coinciden.'); return }
    setCambiandoPass(true)
    try {
      await cambiarPassword(passActual, passNueva)
      setOkPass('Contraseña actualizada correctamente.')
      setPassActual('')
      setPassNueva('')
      setPassConfirmar('')
    } catch (err) {
      setErrorPass(mensajeError(err, 'No se pudo cambiar la contraseña.'))
    } finally {
      setCambiandoPass(false)
    }
  }

  const iniciales = user?.nombre
    ? user.nombre.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
    : 'U'

  return (
    <PanelLayout migas={[{ label: 'Mi perfil' }]}>
      <main className="detalle-main perfil-main">
        <div className="detalle-cabecera">
          <div>
            <div className="detalle-titulo-fila"><h1>Mi perfil</h1></div>
            <div className="detalle-subtitulo">
              {user?.email && <span>{user.email}</span>}
              {user?.nombre_empresa && <span>{user.nombre_empresa}</span>}
            </div>
          </div>
        </div>

        <div className="perfil-grid">
          <form className="card perfil-card" onSubmit={handleGuardar}>
            <div className="card-header">
              <div>
                <div className="card-title">Datos personales y de empresa</div>
                <div className="card-sub">Se usan para identificarte en los reportes y órdenes de trabajo.</div>
              </div>
            </div>
            <div className="card-body perfil-card-body">
              <div className="perfil-avatares">
                <div className="perfil-avatar-bloque">
                  {user?.avatar_url
                    ? <img src={user.avatar_url} alt="Avatar" className="perfil-avatar-img" />
                    : <div className="perfil-avatar-placeholder">{iniciales}</div>}
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => avatarInputRef.current?.click()}
                    disabled={subiendoAvatar}
                  >
                    {subiendoAvatar ? 'Subiendo...' : 'Cambiar avatar'}
                  </button>
                  <input
                    ref={avatarInputRef}
                    type="file"
                    accept=".jpg,.jpeg,.png"
                    style={{ display: 'none' }}
                    onChange={(e) => handleAvatar(e.target.files[0])}
                  />
                </div>

                <div className="perfil-avatar-bloque">
                  {user?.logo_empresa_url
                    ? <img src={user.logo_empresa_url} alt="Logo de empresa" className="perfil-logo-img" />
                    : <div className="perfil-logo-placeholder">Sin logo</div>}
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => logoInputRef.current?.click()}
                    disabled={subiendoLogo}
                  >
                    {subiendoLogo ? 'Subiendo...' : 'Cambiar logo de empresa'}
                  </button>
                  <input
                    ref={logoInputRef}
                    type="file"
                    accept=".jpg,.jpeg,.png"
                    style={{ display: 'none' }}
                    onChange={(e) => handleLogo(e.target.files[0])}
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="nombre">Nombre</label>
                <input
                  id="nombre"
                  type="text"
                  value={form.nombre}
                  onChange={(e) => setCampo('nombre', e.target.value)}
                  disabled={guardando}
                />
              </div>

              <div className="form-group">
                <label htmlFor="descripcion">Descripción <span className="label-opcional">(opcional)</span></label>
                <textarea
                  id="descripcion"
                  rows={3}
                  value={form.descripcion}
                  onChange={(e) => setCampo('descripcion', e.target.value)}
                  disabled={guardando}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="cuit">CUIT <span className="label-opcional">(opcional)</span></label>
                  <input
                    id="cuit"
                    type="text"
                    placeholder="20-12345678-9"
                    value={form.cuit}
                    onChange={(e) => setCampo('cuit', e.target.value)}
                    disabled={guardando}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="telefono">Teléfono de contacto <span className="label-opcional">(opcional)</span></label>
                  <input
                    id="telefono"
                    type="text"
                    value={form.telefono_contacto}
                    onChange={(e) => setCampo('telefono_contacto', e.target.value)}
                    disabled={guardando}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="matricula">Matrícula de aplicador <span className="label-opcional">(opcional)</span></label>
                  <input
                    id="matricula"
                    type="text"
                    value={form.matricula_aplicador}
                    onChange={(e) => setCampo('matricula_aplicador', e.target.value)}
                    disabled={guardando}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="empresa">Nombre de empresa <span className="label-opcional">(opcional)</span></label>
                  <input
                    id="empresa"
                    type="text"
                    value={form.nombre_empresa}
                    onChange={(e) => setCampo('nombre_empresa', e.target.value)}
                    disabled={guardando}
                  />
                </div>
              </div>

              {error && <p className="error-message">{error}</p>}
              {ok && <p className="success-message">{ok}</p>}

              <div className="modal-actions">
                <button type="submit" className="btn-primary" disabled={guardando}>
                  {guardando ? 'Guardando...' : 'Guardar cambios'}
                </button>
              </div>
            </div>
          </form>

          <div className="perfil-columna-lateral">
            <form className="card perfil-card" onSubmit={handleCambiarPassword}>
              <div className="card-header">
                <div>
                  <div className="card-title">Cambiar contraseña</div>
                  <div className="card-sub">Vas a necesitar tu contraseña actual para confirmarlo.</div>
                </div>
              </div>
              <div className="card-body perfil-card-body">
                <div className="form-group">
                  <label htmlFor="pass_actual">Contraseña actual</label>
                  <input
                    id="pass_actual"
                    type="password"
                    value={passActual}
                    onChange={(e) => setPassActual(e.target.value)}
                    disabled={cambiandoPass}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="pass_nueva">Contraseña nueva</label>
                  <input
                    id="pass_nueva"
                    type="password"
                    value={passNueva}
                    onChange={(e) => setPassNueva(e.target.value)}
                    disabled={cambiandoPass}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="pass_confirmar">Confirmar contraseña nueva</label>
                  <input
                    id="pass_confirmar"
                    type="password"
                    value={passConfirmar}
                    onChange={(e) => setPassConfirmar(e.target.value)}
                    disabled={cambiandoPass}
                  />
                </div>

                {errorPass && <p className="error-message">{errorPass}</p>}
                {okPass && <p className="success-message">{okPass}</p>}

                <div className="modal-actions">
                  <button type="submit" className="btn-primary" disabled={cambiandoPass}>
                    {cambiandoPass ? 'Cambiando...' : 'Cambiar contraseña'}
                  </button>
                </div>
              </div>
            </form>

            <form className="card perfil-card" onSubmit={handleGuardarPreferencias}>
              <div className="card-header">
                <div>
                  <div className="card-title">Preferencias de uso</div>
                  <div className="card-sub">Valores por defecto para no elegirlos en cada análisis.</div>
                </div>
              </div>
              <div className="card-body perfil-card-body">
                <div className="form-group">
                  <label htmlFor="indice_preferido">Índice preferido <span className="label-opcional">(opcional)</span></label>
                  <select
                    id="indice_preferido"
                    value={preferencias.indice_preferido}
                    onChange={(e) => setCampoPreferencia('indice_preferido', e.target.value)}
                    disabled={guardandoPreferencias}
                  >
                    <option value="">Sin preferencia</option>
                    {INDICES_PREFERIDOS.map((i) => (
                      <option key={i.value} value={i.value}>{i.label}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="unidad_area_preferida">Unidad de área <span className="label-opcional">(opcional)</span></label>
                  <select
                    id="unidad_area_preferida"
                    value={preferencias.unidad_area_preferida}
                    onChange={(e) => setCampoPreferencia('unidad_area_preferida', e.target.value)}
                    disabled={guardandoPreferencias}
                  >
                    <option value="">Sin preferencia</option>
                    {UNIDADES_AREA.map((u) => (
                      <option key={u.value} value={u.value}>{u.label}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="producto_habitual">Producto habitual <span className="label-opcional">(opcional)</span></label>
                  <select
                    id="producto_habitual"
                    value={preferencias.producto_habitual_id}
                    onChange={(e) => setCampoPreferencia('producto_habitual_id', e.target.value)}
                    disabled={guardandoPreferencias}
                  >
                    <option value="">Sin preferencia</option>
                    {productos.map((p) => (
                      <option key={p.id} value={p.id}>{p.nombre}</option>
                    ))}
                  </select>
                </div>

                {errorPreferencias && <p className="error-message">{errorPreferencias}</p>}
                {okPreferencias && <p className="success-message">{okPreferencias}</p>}

                <div className="modal-actions">
                  <button type="submit" className="btn-primary" disabled={guardandoPreferencias}>
                    {guardandoPreferencias ? 'Guardando...' : 'Guardar preferencias'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </main>
    </PanelLayout>
  )
}
