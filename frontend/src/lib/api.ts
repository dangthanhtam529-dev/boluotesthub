const BASE_URL = import.meta.env.VITE_API_URL

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("access_token")
  if (!token) {
    throw new Error("未登录")
  }
  
  if (!BASE_URL) {
    throw new Error("API地址未配置")
  }
  
  const url = `${BASE_URL}${path}`
  
  const res = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  }).catch((err) => {
    console.error("Fetch error:", err, "URL:", url)
    throw new Error(`网络请求失败: ${err.message}`)
  })
  
  if (res.status === 401) {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
    throw new Error("登录已过期")
  }
  
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}))
    throw new Error(payload.detail || `请求失败: ${res.status}`)
  }
  
  return res.json()
}

export async function apiGet<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "GET" })
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  })
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "PUT",
    body: body ? JSON.stringify(body) : undefined,
  })
}

export async function apiDelete<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "DELETE" })
}
