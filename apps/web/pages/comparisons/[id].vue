<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const route = useRoute()
const { api } = useApi()
const id = route.params.id as string

interface CaseRow {
  case_name: string
  classification: string
  severity: string
  baseline_pass: boolean
  candidate_pass: boolean
}

interface Detail {
  id: string
  baseline_pass_rate: number | null
  candidate_pass_rate: number | null
  pass_rate_delta: number | null
  ai_summary: string | null
  ai_summary_status: string | null
  cases: CaseRow[]
}

const detail = ref<Detail | null>(null)
const summarizing = ref(false)

onMounted(async () => {
  detail.value = await api<Detail>(`/comparisons/${id}`)
})

async function generateSummary() {
  if (!confirm('Generate AI comparison summary? This may incur API cost.')) return
  summarizing.value = true
  try {
    const res = await api<{ ai_summary: string }>(`/comparisons/${id}/summary`, {
      method: 'POST',
      body: JSON.stringify({ confirm: true }),
    })
    if (detail.value) {
      detail.value.ai_summary = res.ai_summary
      detail.value.ai_summary_status = 'completed'
    }
  } finally {
    summarizing.value = false
  }
}
</script>

<template>
  <div>
    <NuxtLink to="/comparisons" class="text-sm text-[var(--accent)]">← Comparisons</NuxtLink>
    <h1 class="mt-2 text-2xl font-semibold">Comparison</h1>

    <div v-if="detail" class="mt-4 flex flex-wrap gap-4 text-sm">
      <span>Baseline pass: {{ detail.baseline_pass_rate != null ? Math.round(detail.baseline_pass_rate * 100) : '—' }}%</span>
      <span>Candidate pass: {{ detail.candidate_pass_rate != null ? Math.round(detail.candidate_pass_rate * 100) : '—' }}%</span>
      <span>Delta: {{ detail.pass_rate_delta != null ? (detail.pass_rate_delta * 100).toFixed(1) : '—' }}%</span>
      <button
        type="button"
        class="rounded border px-2 py-1 text-xs"
        :disabled="summarizing"
        @click="generateSummary"
      >
        {{ summarizing ? 'Summarizing...' : 'AI summary' }}
      </button>
    </div>

    <pre
      v-if="detail?.ai_summary"
      class="mt-4 whitespace-pre-wrap rounded-lg border border-[var(--border)] bg-slate-50 p-4 text-sm"
    >{{ detail.ai_summary }}</pre>

    <ul v-if="detail" class="mt-8 space-y-2">
      <li
        v-for="c in detail.cases"
        :key="c.case_name"
        class="rounded-lg border border-[var(--border)] px-4 py-3 text-sm"
      >
        <span class="font-medium">{{ c.case_name }}</span>
        <span class="ml-2 text-[var(--muted)]">{{ c.classification }} ({{ c.severity }})</span>
        <span class="ml-2">{{ c.baseline_pass ? 'B✓' : 'B✗' }} → {{ c.candidate_pass ? 'C✓' : 'C✗' }}</span>
      </li>
    </ul>
  </div>
</template>
