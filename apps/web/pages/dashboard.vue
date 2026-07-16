<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface DashboardData {
  total_agents: number
  active_versions: number
  draft_versions: number
  recent_regressions: number
  estimated_cost: number
}

const { api } = useApi()
const dashboard = ref<DashboardData | null>(null)

onMounted(async () => {
  dashboard.value = await api<DashboardData>('/dashboard')
})
</script>

<template>
  <div>
    <div class="mb-8 flex items-end justify-between">
      <div>
        <h1 class="text-3xl font-semibold">Dashboard</h1>
        <p class="mt-1 text-[var(--muted)]">Overview of your agents and evaluations</p>
      </div>
      <NuxtLink
        to="/agents/new"
        class="rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
      >
        Create Agent
      </NuxtLink>
    </div>

    <div v-if="dashboard" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div class="rounded-xl border border-[var(--border)] bg-white p-5">
        <p class="text-sm text-[var(--muted)]">Total agents</p>
        <p class="mt-1 text-3xl font-semibold">{{ dashboard.total_agents }}</p>
      </div>
      <div class="rounded-xl border border-[var(--border)] bg-white p-5">
        <p class="text-sm text-[var(--muted)]">Active versions</p>
        <p class="mt-1 text-3xl font-semibold">{{ dashboard.active_versions }}</p>
      </div>
      <div class="rounded-xl border border-[var(--border)] bg-white p-5">
        <p class="text-sm text-[var(--muted)]">Recent regressions</p>
        <p class="mt-1 text-3xl font-semibold">{{ dashboard.recent_regressions }}</p>
      </div>
      <div class="rounded-xl border border-[var(--border)] bg-white p-5">
        <p class="text-sm text-[var(--muted)]">Estimated cost</p>
        <p class="mt-1 text-3xl font-semibold">${{ dashboard.estimated_cost.toFixed(2) }}</p>
      </div>
    </div>

    <div class="mt-8 rounded-xl border border-dashed border-[var(--border)] bg-white/60 p-8 text-center">
      <h2 class="text-lg font-medium">No agents yet</h2>
      <p class="mt-2 text-[var(--muted)]">Create your first agent to start testing and evaluating.</p>
      <NuxtLink
        to="/agents/new"
        class="mt-4 inline-block rounded-lg border border-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent)] hover:bg-teal-50"
      >
        Create First Agent
      </NuxtLink>
    </div>
  </div>
</template>
