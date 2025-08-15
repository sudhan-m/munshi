import React, { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

const apiRequest = async (url, options = {}) => {
  const token = localStorage.getItem('token')
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
    ...options,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }
  
  return response.json()
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      verifyToken()
    } else {
      setLoading(false)
    }
  }, [])

  const verifyToken = async () => {
    try {
      const userData = await apiRequest('/api/auth/verify')
      setUser(userData)
    } catch (error) {
      console.error('Token verification failed:', error)
      logout()
    } finally {
      setLoading(false)
    }
  }

  const login = async (email, password) => {
    try {
      const data = await apiRequest('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      
      const { access_token, user: userData } = data
      localStorage.setItem('token', access_token)
      setUser(userData)
      
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const register = async (email, username, password) => {
    try {
      await apiRequest('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, username, password }),
      })
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem('token')
  }

  const value = { user, loading, login, register, logout }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}