<template>
  <div class="min-h-screen">
    <header class="border-b border-[var(--border)] bg-white/80 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <NuxtLink to="/dashboard" class="text-xl font-semibold tracking-tight text-[var(--accent)]">
          AgentLab
        </NuxtLink>
        <nav class="flex flex-wrap items-center gap-4 text-sm text-[var(--muted)] sm:gap-6">
          <NuxtLink to="/dashboard" class="hover:text-[var(--text)]">Dashboard</NuxtLink>
          <NuxtLink to="/agents" class="hover:text-[var(--text)]">Agents</NuxtLink>
          <NuxtLink to="/playground" class="hover:text-[var(--text)]">Playground</NuxtLink>
          <NuxtLink to="/templates" class="hover:text-[var(--text)]">Templates</NuxtLink>
          <NuxtLink to="/learning" class="hover:text-[var(--text)]">Learning</NuxtLink>
          <NuxtLink to="/knowledge" class="hover:text-[var(--text)]">Knowledge</NuxtLink>
          <NuxtLink to="/evaluations" class="hover:text-[var(--text)]">Evaluations</NuxtLink>
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
