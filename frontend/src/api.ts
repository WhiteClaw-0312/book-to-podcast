// API 配置
const API_BASE = import.meta.env.VITE_API_BASE || ''

export async function apiFetch(path: string, options?: RequestInit) {
  const url = API_BASE + path
  
  // 如果 body 是 FormData，不设置 Content-Type（让浏览器自动设置）
  const isFormData = options?.body instanceof FormData
  
  const headers: Record<string, string> = {
    ...options?.headers,
  }
  
  // 只有非 FormData 时才设置 Content-Type
  if (!isFormData) {
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