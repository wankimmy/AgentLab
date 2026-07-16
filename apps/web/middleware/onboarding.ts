export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/onboarding' || to.path === '/login') return

  const { api } = useApi()
  try {
    const dashboard = await api<{ onboarding_complete: boolean }>('/dashboard')
    if (!dashboard.onboarding_complete && to.path !== '/onboarding') {
      return navigateTo('/onboarding')
    }
  } catch {
    // auth middleware handles unauthenticated users
  }
})
