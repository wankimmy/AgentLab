<script setup lang="ts">
import { checkPromptCompleteness, completenessScore } from '~/utils/promptCompleteness'

definePageMeta({ middleware: ['auth', 'onboarding'] })

const route = useRoute()
const agentId = route.params.id as string

interface AgentVersion {
  id: string
  version_number: number
  system_prompt: string
  release_status: string
  runtime_type: string
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
const newRuntimeType = ref<'native' | 'langgraph'>('native')
const creating = ref(false)
const releaseBusy = ref(false)
const releaseMsg = ref('')
const analyseBusy = ref(false)
const recommendations = ref<{ id: string; suggestions: { title: string; detail: string }[]; status: string }[]>([])

const promptChecks = computed(() => {
  const prompt = agent.value?.active_version?.system_prompt || ''
  return checkPromptCompleteness(prompt)
})
const promptScore = computed(() => completenessScore(promptChecks.value))

onMounted(async () => {
  agent.value = await api<Agent>(`/agents/${agentId}`)
  versions.value = await api<AgentVersion[]>(`/agents/${agentId}/versions`)
  if (agent.value?.active_version?.id) {
    await loadRecommendations(agent.value.active_version.id)
  }
})

async function loadRecommendations(versionId: string) {
  recommendations.value = await api(`/agents/${agentId}/versions/${versionId}/prompt/recommendations`)
}

async function analysePrompt() {
  const vid = agent.value?.active_version?.id
  if (!vid) return
  if (!confirm('Run prompt analysis? Suggestions stay drafts until you apply them manually.')) return
  analyseBusy.value = true
  try {
    await api(`/agents/${agentId}/versions/${vid}/prompt/analyse`, {
      method: 'POST',
      body: JSON.stringify({ confirm: true }),
    })
    await loadRecommendations(vid)
  } finally {
    analyseBusy.value = false
  }
}

async function dismissRec(recId: string) {
  const vid = agent.value?.active_version?.id
  if (!vid) return
  await api(`/agents/${agentId}/versions/${vid}/prompt/recommendations/${recId}/dismiss`, {
    method: 'POST',
  })
  await loadRecommendations(vid)
}

async function createVersion() {
  creating.value = true
  try {
    await api(`/agents/${agentId}/versions`, {
      method: 'POST',
      body: JSON.stringify({
        system_prompt: newPrompt.value || undefined,
        runtime_type: newRuntimeType.value,
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

async function releaseCheck(versionId: string) {
  releaseBusy.value = true
  releaseMsg.value = ''
  try {
    const res = await api<{ status: string; findings: Record<string, unknown> }>(
      `/agents/${agentId}/versions/${versionId}/release-check`,
      { method: 'POST', body: JSON.stringify({}) },
    )
    releaseMsg.value = `Release check: ${res.status}`
    versions.value = await api<AgentVersion[]>(`/agents/${agentId}/versions`)
  } catch (e: unknown) {
    releaseMsg.value = e instanceof Error ? e.message : 'Release check failed'
  } finally {
    releaseBusy.value = false
  }
}

async function markReleaseReady(versionId: string) {
  releaseBusy.value = true
  releaseMsg.value = ''
  try {
    const res = await api<{ release_status: string }>(
      `/agents/${agentId}/versions/${versionId}/mark-release-ready`,
      { method: 'POST', body: JSON.stringify({}) },
    )
    releaseMsg.value = `Status: ${res.release_status}`
    versions.value = await api<AgentVersion[]>(`/agents/${agentId}/versions`)
  } catch (e: unknown) {
    releaseMsg.value = e instanceof Error ? e.message : 'Mark ready failed'
  } finally {
    releaseBusy.value = false
  }
}
</script>

<template>
  <div v-if="agent">
    <NuxtLink to="/agents" class="text-sm text-[var(--muted)] hover:text-[var(--accent)]">← Back to agents</NuxtLink>
    <h1 class="mt-4 text-3xl font-semibold">{{ agent.name }}</h1>
    <p class="mt-1 text-[var(--muted)]">{{ agent.status }} · Active v{{ agent.active_version?.version_number }}</p>

    <div v-if="agent.active_version" class="mt-4">
      <NuxtLink
        :to="`/playground/${agent.active_version.id}?agentId=${agent.id}`"
        class="inline-block rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
      >
        Open playground
      </NuxtLink>
    </div>

    <section class="mt-8 rounded-xl border border-[var(--border)] bg-white p-6">
      <h2 class="text-lg font-medium">Prompt improvement</h2>
      <p class="mt-1 text-sm text-[var(--muted)]">Completeness score: {{ promptScore }}%</p>
      <ul class="mt-2 text-sm text-[var(--muted)]">
        <li v-for="item in promptChecks" :key="item.id">
          {{ item.met ? '✓' : '○' }} {{ item.label }}
        </li>
      </ul>
      <button
        type="button"
        class="mt-3 rounded-lg border px-3 py-2 text-sm"
        :disabled="analyseBusy"
        @click="analysePrompt"
      >
        {{ analyseBusy ? 'Analysing...' : 'Analyse prompt' }}
      </button>
      <ul v-if="recommendations.length" class="mt-4 space-y-3">
        <li
          v-for="rec in recommendations"
          :key="rec.id"
          class="rounded-lg border border-[var(--border)] p-3 text-sm"
        >
          <p class="font-medium">{{ rec.status }} · {{ rec.suggestions.length }} suggestions</p>
          <ul class="mt-2 list-disc pl-5 text-[var(--muted)]">
            <li v-for="(s, idx) in rec.suggestions" :key="idx">{{ s.title }} — {{ s.detail }}</li>
          </ul>
          <button type="button" class="mt-2 text-[var(--accent)]" @click="dismissRec(rec.id)">
            Dismiss
          </button>
        </li>
      </ul>
    </section>

    <section class="mt-8 rounded-xl border border-[var(--border)] bg-white p-6">
      <h2 class="text-lg font-medium">Active prompt</h2>
      <pre class="mono mt-3 whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm">{{ agent.active_version?.system_prompt }}</pre>
    </section>

    <section class="mt-8">
      <h2 class="text-lg font-medium">Versions</h2>
      <p v-if="releaseMsg" class="mt-2 text-sm text-[var(--muted)]">{{ releaseMsg }}</p>
      <div class="mt-4 space-y-3">
        <div
          v-for="version in versions"
          :key="version.id"
          class="rounded-lg border border-[var(--border)] bg-white p-4"
        >
          <div class="flex items-center justify-between">
            <span class="font-medium">v{{ version.version_number }}</span>
            <div class="flex items-center gap-3">
              <NuxtLink
                :to="`/playground/${version.id}?agentId=${agentId}`"
                class="text-sm text-[var(--accent)] hover:underline"
              >
                Playground
              </NuxtLink>
              <button
                type="button"
                class="text-sm text-[var(--accent)]"
                :disabled="releaseBusy"
                @click="releaseCheck(version.id)"
              >
                Release check
              </button>
              <button
                type="button"
                class="text-sm text-[var(--muted)]"
                :disabled="releaseBusy"
                @click="markReleaseReady(version.id)"
              >
                Mark ready
              </button>
              <span class="text-sm text-[var(--muted)]">{{ version.release_status }} · {{ version.runtime_type }}</span>
            </div>
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
      <label class="mt-3 block text-sm font-medium">Runtime</label>
      <select
        v-model="newRuntimeType"
        class="mt-1 rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
      >
        <option value="native">Native (default)</option>
        <option value="langgraph">LangGraph</option>
      </select>
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
