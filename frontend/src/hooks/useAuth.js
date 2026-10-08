import { useState, useCallback } from 'react'
import client from '../api/client'

export function useAuth() {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('usuario')
    return stored ? JSON.parse(stored) : null
  })

  const login = useCallback(async (email, password) => {
    const { data: tokens } = await client.post('/auth/login', { email, password })
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)

    const { data: usuario } = await client.get('/auth/me')
    localStorage.setItem('usuario', JSON.stringify(usuario))
    setUser(usuario)
    return usuario
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('usuario')
    setUser(null)
  }, [])

  // Sincroniza localStorage + estado tras editar perfil/avatar/logo — login()
  // es el único lugar que los seteaba hasta HU-R4-10.
  const actualizarUsuario = useCallback((usuario) => {
    localStorage.setItem('usuario', JSON.stringify(usuario))
    setUser(usuario)
  }, [])

  return {
    user,
    isAuthenticated: !!user,
    login,
    logout,
    actualizarUsuario,
  }
}
