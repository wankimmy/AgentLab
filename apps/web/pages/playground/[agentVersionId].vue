<script setup lang="ts">
import { usePlaygroundStore } from '~/stores/playground'
import type { ChatMessage } from '~/components/ChatPanel.vue'
import type { TraceData } from '~/components/TracePanel.vue'

definePageMeta({ middleware: ['auth', 'onboarding'] })

const route = useRoute()
const versionId = route.params.agentVersionId as string
const agentId = (route.query.agentId as string) || ''

const { api } = useApi()
const { streamPost } = useSSE()
const store = usePlaygroundStore()

const messages = ref<ChatMessage[]>([])
const conversationId = ref<string | null>(null)
const streaming = ref(false)
const streamingContent = ref('')
const trace = ref<TraceData | null>(null)
const traceLoading = ref(false)
const saving = ref(false)
const mobileTab = ref<'chat' | 'config' | 'trace'>('chat')

interface AgentVersion {
  id: string
  agent_id: string
  system_prompt: string
  model: string
  model_settings: { temperature?: number }
  memory_config: { mode?: string }
}

onMounted(async () => {
  const resolvedAgentId = agentId || (await resolveAgentId())
  if (!resolvedAgentId) {
    await navigateTo('/playground')
    return
  }
  const version = await api<AgentVersion>(`/agents/${resolvedAgentId}/versions/${versionId}`)
  store.initFromVersion(resolvedAgentId, versionId, version)
  await ensureConversation(resolvedAgentId)
})

async function resolveAgentId(): Promise<string | null> {
  const agents = await api<{ items: Array<{ id: string; active_version?: { id: string } }> }>(
    '/agents',
  )
  const match = agents.items.find((a) => a.active_version?.id === versionId)
  return match?.id ?? null
}

async function ensureConversation(aid: string) {
  const list = await api<Array<{ id: string; agent_version_id: string }>>(
    `/conversations?agent_id=${aid}`,
  )
  const existing = list.find((c) => c.agent_version_id === versionId)
  if (existing) {
    conversationId.value = existing.id
    await loadConversation(existing.id)
    return
  }
  const created = await api<{ id: string }>('/conversations', {
    method: 'POST',
    body: JSON.stringify({
      agent_id: aid,
      agent_version_id: versionId,
      title: 'Playground session',
    }),
  })
  conversationId.value = created.id
}

async function loadConversation(id: string) {
  const conv = await api<{
    messages: Array<{
      id: string
      role: string
      content: string
      trace_id?: string | null
      feedback_rating?: number | null
    }>
  }>(`/conversations/${id}`)
  messages.value = conv.messages
  const lastAssistant = [...conv.messages].reverse().find((m) => m.role === 'assistant')
  if (lastAssistant?.trace_id) await loadTrace(lastAssistant.trace_id)
}

async function loadTrace(traceId: string) {
  traceLoading.value = true
  try {
    trace.value = await api<TraceData>(`/traces/${traceId}`)
  } finally {
    traceLoading.value = false
  }
}

async function sendMessage(content: string) {
  if (!conversationId.value) return
  streaming.value = true
  streamingContent.value = ''
  const overrides = store.apiOverrides
  try {
    await streamPost(
      `/conversations/${conversationId.value}/messages`,
      { content, overrides },
      async (evt) => {
        if (evt.event === 'token') {
          streamingContent.value += String(evt.data.content || '')
        }
        if (evt.event === 'done' && evt.data.trace_id) {
          await loadConversation(conversationId.value!)
        }
        if (evt.event === 'error') {
          throw new Error(String(evt.data.message || 'Stream error'))
        }
      },
    )
  } finally {
    streaming.value = false
    streamingContent.value = ''
  }
}

async function submitFeedback(messageId: string, rating: number, notes: string) {
  await api(`/messages/${messageId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ rating, notes }),
  })
  const msg = messages.value.find((m) => m.id === messageId)
  if (msg) msg.feedback_rating = rating
}

async function saveAsVersion() {
  saving.value = true
  try {
    const eff = store.effective
    await api(`/agents/${store.agentId}/versions`, {
      method: 'POST',
      body: JSON.stringify({
        system_prompt: eff.system_prompt,
        model: eff.model,
        change_summary: 'Saved from playground overrides',
      }),
    })
    store.discard()
    const version = await api<AgentVersion>(
      `/agents/${store.agentId}/versions/${versionId}`,
    )
    store.initFromVersion(store.agentId, versionId, version)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <NuxtLink to="/playground" class="text-sm text-[var(--accent)]">← Playground</NuxtLink>
        <h1 class="mt-1 text-2xl font-semibold">Playground</h1>
      </div>
      <div v-if="store.isDirty" class="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm">
        <span class="text-amber-900">Overrides active</span>
        <button type="button" class="underline" @click="store.discard()">Discard</button>
        <button
          type="button"
          class="rounded bg-[var(--accent)] px-3 py-1 text-white"
          :disabled="saving"
          @click="saveAsVersion"
        >
          {{ saving ? 'Saving...' : 'Save as new version' }}
        </button>
      </div>
    </div>

    <div class="mb-4 flex gap-2 lg:hidden">
      <button
        v-for="tab in ['chat', 'config', 'trace'] as const"
        :key="tab"
        type="button"
        class="rounded-lg px-3 py-1.5 text-sm capitalize"
        :class="mobileTab === tab ? 'bg-[var(--accent)] text-white' : 'border border-[var(--border)]'"
        @click="mobileTab = tab"
      >
        {{ tab }}
      </button>
    </div>

    <div class="grid gap-4 lg:grid-cols-12">
      <aside class="lg:col-span-3" :class="mobileTab === 'config' ? 'block' : 'hidden lg:block'">
        <h2 class="mb-2 text-sm font-medium">Config</h2>
        <PlaygroundConfigPanel />
      </aside>
      <section class="lg:col-span-5" :class="mobileTab === 'chat' ? 'block' : 'hidden lg:block'">
        <ChatPanel
          :messages="messages"
          :streaming="streaming"
          :streaming-content="streamingContent"
          @send="sendMessage"
          @feedback="submitFeedback"
        />
      </section>
      <aside class="lg:col-span-4" :class="mobileTab === 'trace' ? 'block' : 'hidden lg:block'">
        <TracePanel :trace="trace" :loading="traceLoading" />
      </aside>
    </div>
  </div>
</template>
