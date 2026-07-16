<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const route = useRoute()
const agentId = route.params.id as string

interface AgentVersion {
  id: string
  version_number: number
  system_prompt: string
  release_status: string
  created_at?: string
}

interface Agent {
  id: string
  name: string
  description: string | null
  status: string
  active_version?: AgentVersion
}

const { api } = useApi()
const agent = ref<Agent | null>(null)
const versions = ref<AgentVersion[]>([])
const newPrompt = ref('')
const creating = ref(false)

onMounted(async () => {
  agent.value = await api<Agent>(`/agents/${agentId}`)
  versions.value = await api<AgentVersion[]>(`/agents/${agentId}/versions`)
})

async function createVersion() {
  creating.value = true
  try {
    await api(`/agents/${agentId}/versions`, {
      method: 'POST',
      body: JSON.stringify({
        system_prompt: newPrompt.value || undefined,
        change_summary: 'Manual version from UI',
      }),
    })
    versions.value = await api<AgentVersion[]>(`/agents/${agentId}/versions`)
    agent.value = await api<Agent>(`/agents/${agentId}`)
    newPrompt.value = ''
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div v-if="agent">
    <NuxtLink to="/agents" class="text-sm text-[var(--muted)] hover:text-[var(--accent)]">← Back to agents</NuxtLink>
    <h1 class="mt-4 text-3xl font-semibold">{{ agent.name }}</h1>
    <p class="mt-1 text-[var(--muted)]">{{ agent.status }} · Active v{{ agent.active_version?.version_number }}</p>

    <section class="mt-8 rounded-xl border border-[var(--border)] bg-white p-6">
      <h2 class="text-lg font-medium">Active prompt</h2>
      <pre class="mono mt-3 whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm">{{ agent.active_version?.system_prompt }}</pre>
    </section>

    <section class="mt-8">
      <h2 class="text-lg font-medium">Versions</h2>
      <div class="mt-4 space-y-3">
        <div
          v-for="version in versions"
          :key="version.id"
          class="rounded-lg border border-[var(--border)] bg-white p-4"
        >
          <div class="flex items-center justify-between">
            <span class="font-medium">v{{ version.version_number }}</span>
            <span class="text-sm text-[var(--muted)]">{{ version.release_status }}</span>
          </div>
          <p class="mt-2 line-clamp-2 text-sm text-[var(--muted)]">{{ version.system_prompt }}</p>
        </div>
      </div>
    </section>

    <section class="mt-8 rounded-xl border border-[var(--border)] bg-white p-6">
      <h2 class="text-lg font-medium">Create new version</h2>
      <textarea
        v-model="newPrompt"
        rows="4"
        class="mt-3 w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
        placeholder="Optional new system prompt (copies active version if empty)"
      />
      <button
        class="mt-3 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
        :disabled="creating"
        @click="createVersion"
      >
        {{ creating ? 'Creating...' : 'Create Version' }}
      </button>
    </section>
  </div>
</template>
