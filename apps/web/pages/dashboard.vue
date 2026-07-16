<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

interface DashboardData {
  total_agents: number
  active_versions: number
  draft_versions: number
  onboarding_complete: boolean
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
    <div
      v-if="dashboard && !dashboard.onboarding_complete"
      class="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm"
    >
      <p class="font-medium text-amber-900">Finish onboarding to unlock the full workflow</p>
      <NuxtLink to="/onboarding" class="mt-2 inline-block text-[var(--accent)] hover:underline">
        Resume onboarding →
      </NuxtLink>
    </div>

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

    <EmptyState
      v-if="dashboard && dashboard.total_agents === 0"
      class="mt-8"
      title="No agents yet"
      description="Create your first agent, start from a template, or install the ERP sample pack."
      :actions="[
        { label: 'Create agent', to: '/agents/new', primary: true },
        { label: 'Choose template', to: '/templates' },
        { label: 'Install sample pack', to: '/sample-packs' },
      ]"
    />
  </div>
</template>
