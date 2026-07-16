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
const pendingApproval = ref<{
  approval_id: string
  tool: string
  arguments: Record<string, unknown>
} | null>(null)
const approvalBusy = ref(false)
const toolActivity = ref<string[]>([])

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
  pendingApproval.value = null
  toolActivity.value = []
  const overrides = store.apiOverrides
  try {
    await streamPost(
      `/conversations/${conversationId.value}/messages`,
      { content, overrides },
      async (evt) => {
        if (evt.event === 'token') {
          streamingContent.value += String(evt.data.content || '')
        }
        if (evt.event === 'tool_call') {
          toolActivity.value.push(`Called ${evt.data.tool}`)
        }
        if (evt.event === 'tool_result') {
          toolActivity.value.push(`Result: ${evt.data.tool} (${evt.data.status})`)
        }
        if (evt.event === 'approval_required') {
          pendingApproval.value = {
            approval_id: String(evt.data.approval_id),
            tool: String(evt.data.tool),
            arguments: (evt.data.arguments as Record<string, unknown>) || {},
          }
        }
        if (evt.event === 'done' && evt.data.trace_id) {
          pendingApproval.value = null
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
    pendingApproval.value = null
  }
}

async function decideApproval(approve: boolean) {
  if (!pendingApproval.value) return
  approvalBusy.value = true
  const { api } = useApi()
  const path = approve ? 'approve' : 'reject'
  try {
    await api(`/tool-approvals/${pendingApproval.value.approval_id}/${path}`, {
      method: 'POST',
    })
  } finally {
    approvalBusy.value = false
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
        <div
          v-if="pendingApproval"
          class="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm"
        >
          <p class="font-medium text-amber-900">Tool approval required: {{ pendingApproval.tool }}</p>
          <pre class="mono mt-2 text-xs">{{ JSON.stringify(pendingApproval.arguments, null, 2) }}</pre>
          <div class="mt-3 flex gap-2">
            <button
              type="button"
              class="rounded bg-[var(--accent)] px-3 py-1.5 text-white disabled:opacity-50"
              :disabled="approvalBusy"
              @click="decideApproval(true)"
            >
              Approve
            </button>
            <button
              type="button"
              class="rounded border border-[var(--border)] px-3 py-1.5 disabled:opacity-50"
              :disabled="approvalBusy"
              @click="decideApproval(false)"
            >
              Reject
            </button>
          </div>
        </div>
        <ul v-if="toolActivity.length" class="mb-4 space-y-1 text-xs text-[var(--muted)]">
          <li v-for="(line, i) in toolActivity" :key="i">{{ line }}</li>
        </ul>
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
