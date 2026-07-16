<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

interface Agent {
  id: string
  name: string
  status: string
  risk_level: string
  active_version?: { version_number: number }
}

interface AgentList {
  items: Agent[]
  total: number
}

const { api } = useApi()
const agents = ref<Agent[]>([])

onMounted(async () => {
  const data = await api<AgentList>('/agents')
  agents.value = data.items
})
</script>

<template>
  <div>
    <div class="mb-8 flex items-end justify-between">
      <div>
        <h1 class="text-3xl font-semibold">Agents</h1>
        <p class="mt-1 text-[var(--muted)]">Manage your AI agents and versions</p>
      </div>
      <NuxtLink
        to="/agents/new"
        class="rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
      >
        New Agent
      </NuxtLink>
    </div>

    <div class="mb-6 grid gap-6 lg:grid-cols-3">
      <div class="lg:col-span-2">
        <EmptyState
          v-if="agents.length === 0"
          title="No agents yet"
          description="Create an agent from scratch, apply a template, or install a sample pack."
          :actions="[
            { label: 'Create agent', to: '/agents/new', primary: true },
            { label: 'Browse templates', to: '/templates' },
            { label: 'Sample packs', to: '/sample-packs' },
          ]"
        />

        <div v-else class="space-y-3">
          <NuxtLink
            v-for="agent in agents"
            :key="agent.id"
            :to="`/agents/${agent.id}`"
            class="block rounded-xl border border-[var(--border)] bg-white p-5 hover:border-[var(--accent)]"
          >
            <div class="flex items-center justify-between">
              <div>
                <h2 class="font-medium">{{ agent.name }}</h2>
                <p class="mt-1 text-sm text-[var(--muted)]">
                  {{ agent.status }} · {{ agent.risk_level }} risk
                  <span v-if="agent.active_version"> · v{{ agent.active_version.version_number }}</span>
                </p>
              </div>
              <span class="text-[var(--accent)]">View →</span>
            </div>
          </NuxtLink>
        </div>
      </div>
      <HelpPanel
        title="Managing agents"
        why="Each agent has immutable versions so you can test changes safely."
        :steps="['Create or apply template', 'Edit prompt in new version', 'Evaluate before release']"
        :next-action="{ label: 'What is an agent?', to: '/learning/what-is-an-agent' }"
      />
    </div>
  </div>
</template>
