export interface User {
  id: string
  email: string
  role: string
}

export function useAuth() {
  const user = useState<User | null>('auth-user', () => null)

  async function fetchMe() {
    const { api } = useApi()
    try {
      user.value = await api<User>('/auth/me')
    } catch {
      user.value = null
    }
  }

  async function login(email: string, password: string) {
    const { api } = useApi()
    user.value = await api<User>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async function logout() {
    const { api } = useApi()
    await api('/auth/logout', { method: 'POST' })
    user.value = null
    await navigateTo('/login')
  }

  return { user, fetchMe, login, logout }
}
