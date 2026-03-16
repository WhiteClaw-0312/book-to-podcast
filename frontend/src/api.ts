// API 配置 v4.0
// 根据当前域名自动选择 API 地址
const getApiBase = () => {
  // 如果设置了环境变量，使用环境变量
  if (import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE
  }
  
  // GitHub Pages 使用 HTTP 服务器地址
  if (window.location.hostname.includes('github.io')) {
    return 'http://139.196.211.206'
  }
  
  // 本地开发或其他环境，使用相对路径
  return ''
}

const API_BASE = getApiBase()

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
  
  try {
    const response = await fetch(url, {
      ...options,
      headers,
    })
    return response
  } catch (error: any) {
    // 捕获网络错误，抛出更友好的错误信息
    if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
      console.error('API请求失败:', url, error)
      // 返回一个模拟的错误响应
      return {
        ok: false,
        status: 0,
        statusText: 'Network Error',
        json: async () => ({ detail: '网络连接失败，请检查服务器是否在线或是否需要接受安全证书' }),
        text: async () => 'Network Error'
      } as Response
    }
    throw error
  }
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