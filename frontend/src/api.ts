// API 配置 v4.0
const API_BASE = import.meta.env.VITE_API_BASE || ''

export async function apiFetch(path: string, options?: RequestInit & { token?: string }) {
  const url = API_BASE + path
  
  // 如果 body 是 FormData，不设置 Content-Type
  const isFormData = options?.body instanceof FormData
  
  const headers: Record<string, string> = {
    ...options?.headers as Record<string, string>,
  }
  
  // 添加认证token
  const token = options?.token || localStorage.getItem('token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  // 只有非 FormData 时才设置 Content-Type
  if (!isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  
  return fetch(url, {
    ...options,
    headers,
  })
}

export function getApiUrl(path: string) {
  return API_BASE + path
}

// 用户相关
export function getUser(): any {
  const userData = localStorage.getItem('user')
  if (userData) {
    try {
      return JSON.parse(userData)
    } catch {
      return null
    }
  }
  return null
}

export function getToken(): string | null {
  return localStorage.getItem('token')
}

export function isLoggedIn(): boolean {
  return !!getToken()
}

export function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}