import client from './client'

export const obtenerPerfil = () =>
  client.get('/auth/me').then(r => r.data)

export const actualizarPerfil = (data) =>
  client.put('/auth/me', data).then(r => r.data)

export const cambiarPassword = (passwordActual, passwordNueva) =>
  client.post('/auth/me/password', {
    password_actual: passwordActual,
    password_nueva: passwordNueva,
  })

export const subirAvatar = (archivo) => {
  const fd = new FormData()
  fd.append('archivo', archivo)
  return client.post('/auth/me/avatar', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export const subirLogoEmpresa = (archivo) => {
  const fd = new FormData()
  fd.append('archivo', archivo)
  return client.post('/auth/me/logo-empresa', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}
