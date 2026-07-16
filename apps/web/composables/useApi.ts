export function useApi() {
  const config = useRuntimeConfig()

  async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`/api/v1${path}`, {
      ...options,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || 'Request failed')
    }
    if (response.status === 204) {
      return undefined as T
    }
    return response.json()
  }

  return { api, apiBaseUrl: config.apiBaseUrl }
}
