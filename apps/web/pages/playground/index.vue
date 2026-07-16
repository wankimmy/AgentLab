<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

interface Agent {
  id: string
  name: string
  active_version?: { id: string; version_number: number }
}

interface AgentList {
  items: Agent[]
}

const { api } = useApi()
const agents = ref<Agent[]>([])

onMounted(async () => {
  const data = await api<AgentList>('/agents')
  agents.value = data.items.filter((a) => a.active_version)
})
</script>

<template>
  <div>
    <h1 class="text-3xl font-semibold">Playground</h1>
    <p class="mt-1 text-[var(--muted)]">Select an agent version to test</p>

    <EmptyState
      v-if="agents.length === 0"
      class="mt-8"
      title="No agents ready for playground"
      description="Create an agent with an active version first."
      :actions="[
        { label: 'Create agent', to: '/agents/new', primary: true },
        { label: 'Browse templates', to: '/templates' },
      ]"
    />

    <div v-else class="mt-8 space-y-3">
      <NuxtLink
        v-for="agent in agents"
        :key="agent.id"
        :to="`/playground/${agent.active_version!.id}?agentId=${agent.id}`"
        class="block rounded-xl border border-[var(--border)] bg-white p-5 hover:border-[var(--accent)]"
      >
        <h2 class="font-medium">{{ agent.name }}</h2>
        <p class="mt-1 text-sm text-[var(--muted)]">Active version v{{ agent.active_version!.version_number }}</p>
      </NuxtLink>
    </div>
  </div>
</template>
