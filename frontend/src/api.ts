// API 配置
const API_BASE = import.meta.env.VITE_API_BASE || ''

export async function apiFetch(path: string, options?: RequestInit) {
  const url = API_BASE + path
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
}

export function getApiUrl(path: string) {
  return API_BASE + path
}