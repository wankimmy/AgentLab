<template>
  <div class="min-h-screen">
    <header class="border-b border-[var(--border)] bg-white/80 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <NuxtLink to="/dashboard" class="text-xl font-semibold tracking-tight text-[var(--accent)]">
          AgentLab
        </NuxtLink>
        <nav class="flex items-center gap-6 text-sm text-[var(--muted)]">
          <NuxtLink to="/dashboard" class="hover:text-[var(--text)]">Dashboard</NuxtLink>
          <NuxtLink to="/agents" class="hover:text-[var(--text)]">Agents</NuxtLink>
          <span class="cursor-not-allowed opacity-50">Knowledge</span>
          <span class="cursor-not-allowed opacity-50">Evaluations</span>
          <button
            v-if="user"
            class="rounded-md border border-[var(--border)] px-3 py-1.5 hover:bg-slate-50"
            @click="logout"
          >
            Log out
          </button>
        </nav>
      </div>
    </header>
    <main class="mx-auto max-w-6xl px-6 py-8">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
const { user, logout, fetchMe } = useAuth()
await fetchMe()
</script>
