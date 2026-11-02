import axios from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    // Un 401 del propio login es "credenciales incorrectas": recargar la página taparía el mensaje.
    const esLogin = error.config?.url?.endsWith('/auth/login')
    if (error.response?.status === 401 && !esLogin) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('usuario')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
