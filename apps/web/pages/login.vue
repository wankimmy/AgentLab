<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const { login } = useAuth()
const { api } = useApi()

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await login(email.value, password.value)
    const dashboard = await api<{ onboarding_complete: boolean }>('/dashboard')
    await navigateTo(dashboard.onboarding_complete ? '/dashboard' : '/onboarding')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h2 class="mb-6 text-xl font-semibold">Sign in</h2>
    <form class="space-y-4" @submit.prevent="handleLogin">
      <div>
        <label class="mb-1 block text-sm text-[var(--muted)]" for="email">Email</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          class="w-full rounded-lg border border-[var(--border)] px-3 py-2"
          placeholder="owner@agentlab.local"
        />
      </div>
      <div>
        <label class="mb-1 block text-sm text-[var(--muted)]" for="password">Password</label>
        <input
          id="password"
          v-model="password"
          type="password"
          required
          class="w-full rounded-lg border border-[var(--border)] px-3 py-2"
        />
      </div>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      <button
        type="submit"
        class="w-full rounded-lg bg-[var(--accent)] px-4 py-2.5 font-medium text-white hover:bg-[var(--accent-hover)]"
        :disabled="loading"
      >
        {{ loading ? 'Signing in...' : 'Sign in' }}
      </button>
    </form>
  </div>
</template>
