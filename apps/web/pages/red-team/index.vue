<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const { api } = useApi()
const agentVersionId = ref('')
const estimating = ref(false)
const running = ref(false)
const estimate = ref<{ estimated_cost: number; case_count: number } | null>(null)
const runDetail = ref<{ id: string; status: string; cases: { id: string; category: string; passed: boolean | null; payload: string }[] } | null>(null)
const message = ref('')

onMounted(async () => {
  const agents = await api<{ items: { id: string; active_version?: { id: string } }[] }>('/agents')
  const first = agents.items[0]
  if (first?.active_version?.id) {
    agentVersionId.value = first.active_version.id
  }
})

async function estimateRun() {
  if (!agentVersionId.value) return
  estimating.value = true
  try {
    estimate.value = await api('/red-team/runs/estimate', {
      method: 'POST',
      body: JSON.stringify({ agent_version_id: agentVersionId.value }),
    })
  } finally {
    estimating.value = false
  }
}

async function startRun() {
  if (!agentVersionId.value) return
  if (!confirm('Red-team run sends synthetic attack prompts to the agent. Continue?')) return
  running.value = true
  message.value = ''
  try {
    const run = await api<{ id: string }>('/red-team/runs', {
      method: 'POST',
      body: JSON.stringify({ agent_version_id: agentVersionId.value, confirm: true }),
    })
    runDetail.value = await api(`/red-team/runs/${run.id}`)
    message.value = 'Run completed. Review cases and promote failures into your dataset.'
  } finally {
    running.value = false
  }
}

async function promote(caseId: string) {
  await api(`/red-team/cases/${caseId}/promote`, { method: 'POST' })
  message.value = 'Promoted as draft eval case.'
}
</script>

<template>
  <div>
    <h1 class="text-2xl font-semibold">Red team</h1>
    <p class="mt-1 text-sm text-[var(--muted)]">
      Synthetic attacks (injection, jailbreak, exfil). Results are not auto-added to datasets.
    </p>

    <section class="mt-8 max-w-xl space-y-3 rounded-xl border border-[var(--border)] bg-white p-6">
      <label class="block text-sm font-medium">Agent version ID</label>
      <input v-model="agentVersionId" class="w-full rounded-lg border px-3 py-2 text-sm">
      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="rounded-lg border px-3 py-2 text-sm"
          :disabled="estimating"
          @click="estimateRun"
        >
          Estimate cost
        </button>
        <button
          type="button"
          class="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm text-white"
          :disabled="running || !agentVersionId"
          @click="startRun"
        >
          {{ running ? 'Running...' : 'Run red team' }}
        </button>
      </div>
      <p v-if="estimate" class="text-sm text-[var(--muted)]">
        {{ estimate.case_count }} cases · est. ${{ estimate.estimated_cost.toFixed(4) }}
      </p>
      <p v-if="message" class="text-sm">{{ message }}</p>
    </section>

    <ul v-if="runDetail?.cases?.length" class="mt-8 space-y-2">
      <li
        v-for="c in runDetail.cases"
        :key="c.id"
        class="rounded-lg border border-[var(--border)] px-4 py-3 text-sm"
      >
        <span class="font-medium">{{ c.category }}</span>
        <span class="ml-2">{{ c.passed ? 'PASS' : 'FAIL' }}</span>
        <p class="mt-1 text-[var(--muted)]">{{ c.payload }}</p>
        <button type="button" class="mt-2 text-[var(--accent)]" @click="promote(c.id)">
          Promote to dataset
        </button>
      </li>
    </ul>
  </div>
</template>
