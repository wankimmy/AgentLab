<script setup lang="ts">
definePageMeta({ middleware: ['auth'] })

const STEPS = [
  'Define',
  'Template',
  'Behaviour',
  'Knowledge',
  'Tools',
  'Test cases',
  'Playground',
  'Evaluation',
]

const { api } = useApi()
const step = ref(1)
const saving = ref(false)
const templates = ref<Array<{ id: string; slug: string; name: string; description: string }>>([])
const selectedTemplate = ref<{ id: string; name: string; system_prompt?: string; tool_config?: Record<string, string>; eval_starter_pack?: { cases?: Array<{ name: string }> } } | null>(null)

const defineForm = reactive({
  purpose: '',
  target_audience: '',
  example_questions: '',
  risk_level: 'medium',
  name: '',
  draft_reviewed: false,
})

const behaviour = reactive({ system_prompt: '' })
const tools = reactive<Record<string, string>>({
  calculator: 'auto',
  knowledge_search: 'auto',
  current_datetime: 'auto',
})
const knowledgeChoice = ref<'skip' | 'later'>('skip')

async function loadProgress() {
  const progress = await api<{
    current_step: number
    completed: boolean
    step_data: Record<string, Record<string, unknown>>
  }>('/onboarding/progress')
  if (progress.completed) {
    await navigateTo('/dashboard')
    return
  }
  step.value = progress.current_step
  const data = progress.step_data || {}
  if (data.define) Object.assign(defineForm, data.define)
  if (data.behaviour) Object.assign(behaviour, data.behaviour)
  const toolsData = data.tools as { tool_config?: Record<string, string> } | undefined
  if (toolsData?.tool_config) Object.assign(tools, toolsData.tool_config)
  const templateData = data.template as { template_id?: string } | undefined
  if (templateData?.template_id) {
    const tpl = await api<typeof selectedTemplate.value>(`/templates/${templateData.template_id}`)
    selectedTemplate.value = tpl
    if (!behaviour.system_prompt && tpl?.system_prompt) behaviour.system_prompt = tpl.system_prompt
  }
}

async function saveProgress(nextStep?: number) {
  saving.value = true
  try {
    const payload = {
      current_step: nextStep ?? step.value,
      step_data: {
        define: { ...defineForm },
        template: selectedTemplate.value ? { template_id: selectedTemplate.value.id } : {},
        behaviour: { ...behaviour },
        tools: { tool_config: { ...tools } },
        knowledge: { choice: knowledgeChoice.value },
      },
    }
    await api('/onboarding/progress', { method: 'PUT', body: JSON.stringify(payload) })
    if (nextStep) step.value = nextStep
  } finally {
    saving.value = false
  }
}

async function helpMeDefine() {
  const draft = await api<{
    suggested_name: string
    suggested_purpose: string
    suggested_target_audience: string
    draft_notes: string
  }>('/onboarding/define-draft', {
    method: 'POST',
    body: JSON.stringify({
      purpose: defineForm.purpose,
      target_audience: defineForm.target_audience,
      example_questions: defineForm.example_questions.split('\n').filter(Boolean),
      risk_level: defineForm.risk_level,
    }),
  })
  defineForm.name = draft.suggested_name
  defineForm.purpose = draft.suggested_purpose
  defineForm.target_audience = draft.suggested_target_audience
  defineForm.draft_reviewed = false
}

async function selectTemplate(id: string | null) {
  if (!id) {
    selectedTemplate.value = null
    return
  }
  selectedTemplate.value = await api(`/templates/${id}`)
  if (selectedTemplate.value?.system_prompt) behaviour.system_prompt = selectedTemplate.value.system_prompt
  if (selectedTemplate.value?.tool_config) Object.assign(tools, selectedTemplate.value.tool_config)
}

async function complete() {
  await saveProgress(8)
  await api('/onboarding/complete', { method: 'POST' })
  await navigateTo('/dashboard')
}

const completeness = computed(() => checkPromptCompleteness(behaviour.system_prompt))
const completenessPct = computed(() => completenessScore(completeness.value))
const starterCases = computed(() => selectedTemplate.value?.eval_starter_pack?.cases || [])

onMounted(async () => {
  templates.value = await api('/templates')
  await loadProgress()
})
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-3xl font-semibold">Agent onboarding</h1>
      <p class="mt-1 text-[var(--muted)]">Step {{ step }} of 8 — {{ STEPS[step - 1] }}</p>
      <div class="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
        <div class="h-full bg-[var(--accent)] transition-all" :style="{ width: `${(step / 8) * 100}%` }" />
      </div>
    </div>

    <!-- Step 1: Define -->
    <div v-if="step === 1" class="space-y-4 rounded-xl border border-[var(--border)] bg-white p-6">
      <div>
        <label class="mb-1 block text-sm">Purpose</label>
        <textarea v-model="defineForm.purpose" rows="3" class="w-full rounded-lg border border-[var(--border)] px-3 py-2" placeholder="Help finance staff answer ERP questions from approved manuals." />
      </div>
      <div>
        <label class="mb-1 block text-sm">Target audience</label>
        <input v-model="defineForm.target_audience" class="w-full rounded-lg border border-[var(--border)] px-3 py-2" />
      </div>
      <div>
        <label class="mb-1 block text-sm">Example questions (one per line)</label>
        <textarea v-model="defineForm.example_questions" rows="3" class="w-full rounded-lg border border-[var(--border)] px-3 py-2" />
      </div>
      <div>
        <label class="mb-1 block text-sm">Risk level</label>
        <select v-model="defineForm.risk_level" class="rounded-lg border border-[var(--border)] px-3 py-2">
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </div>
      <button type="button" class="rounded-lg border border-[var(--border)] px-4 py-2 text-sm hover:bg-slate-50" @click="helpMeDefine">
        Help Me Define
      </button>
      <div v-if="defineForm.name" class="rounded-lg bg-slate-50 p-4 text-sm">
        <p><strong>Suggested name:</strong> {{ defineForm.name }}</p>
        <label class="mt-2 flex items-center gap-2">
          <input v-model="defineForm.draft_reviewed" type="checkbox" />
          I have reviewed the draft
        </label>
      </div>
      <div class="flex justify-end gap-3">
        <button
          type="button"
          class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          :disabled="!defineForm.purpose || !defineForm.draft_reviewed"
          @click="saveProgress(2)"
        >
          Continue
        </button>
      </div>
    </div>

    <!-- Step 2: Template -->
    <div v-else-if="step === 2" class="space-y-4">
      <div class="grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          class="rounded-xl border p-4 text-left hover:border-[var(--accent)]"
          :class="!selectedTemplate ? 'border-[var(--accent)] bg-teal-50' : 'border-[var(--border)] bg-white'"
          @click="selectTemplate(null)"
        >
          <p class="font-medium">Start empty</p>
          <p class="mt-1 text-sm text-[var(--muted)]">Configure everything yourself</p>
        </button>
        <button
          v-for="tpl in templates.filter((t) => t.slug !== 'empty')"
          :key="tpl.id"
          type="button"
          class="rounded-xl border p-4 text-left hover:border-[var(--accent)]"
          :class="selectedTemplate?.id === tpl.id ? 'border-[var(--accent)] bg-teal-50' : 'border-[var(--border)] bg-white'"
          @click="selectTemplate(tpl.id)"
        >
          <p class="font-medium">{{ tpl.name }}</p>
          <p class="mt-1 text-sm text-[var(--muted)] line-clamp-2">{{ tpl.description }}</p>
        </button>
      </div>
      <div class="flex justify-between">
        <button type="button" class="text-sm text-[var(--muted)]" @click="step = 1">Back</button>
        <button type="button" class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white" @click="saveProgress(3)">
          Continue
        </button>
      </div>
    </div>

    <!-- Step 3: Behaviour -->
    <div v-else-if="step === 3" class="space-y-4 rounded-xl border border-[var(--border)] bg-white p-6">
      <textarea v-model="behaviour.system_prompt" rows="14" class="mono w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm" />
      <div>
        <p class="text-sm font-medium">Completeness checklist ({{ completenessPct }}%)</p>
        <ul class="mt-2 space-y-1 text-sm">
          <li v-for="item in completeness" :key="item.id" :class="item.met ? 'text-emerald-700' : 'text-[var(--muted)]'">
            {{ item.met ? '✓' : '○' }} {{ item.label }}
          </li>
        </ul>
      </div>
      <div class="flex justify-between">
        <button type="button" class="text-sm text-[var(--muted)]" @click="step = 2">Back</button>
        <button type="button" class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white" @click="saveProgress(4)">
          Continue
        </button>
      </div>
    </div>

    <!-- Step 4: Knowledge -->
    <div v-else-if="step === 4" class="space-y-4 rounded-xl border border-[var(--border)] bg-white p-6">
      <p class="text-[var(--muted)]">Upload approved documents or skip and set up knowledge later.</p>
      <label class="flex items-center gap-2">
        <input v-model="knowledgeChoice" type="radio" value="skip" />
        Skip for now
      </label>
      <label class="flex items-center gap-2">
        <input v-model="knowledgeChoice" type="radio" value="later" />
        Install sample pack later
      </label>
      <NuxtLink to="/knowledge" class="text-sm text-[var(--accent)] hover:underline">Preview knowledge screen →</NuxtLink>
      <div class="flex justify-between">
        <button type="button" class="text-sm text-[var(--muted)]" @click="step = 3">Back</button>
        <button type="button" class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white" @click="saveProgress(5)">
          Continue
        </button>
      </div>
    </div>

    <!-- Step 5: Tools -->
    <div v-else-if="step === 5" class="space-y-4 rounded-xl border border-[var(--border)] bg-white p-6">
      <div v-for="(mode, toolName) in tools" :key="toolName" class="flex items-center justify-between">
        <span class="font-medium">{{ toolName }}</span>
        <select v-model="tools[toolName]" class="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm">
          <option value="auto">Auto</option>
          <option value="approval">Approval required</option>
          <option value="disabled">Disabled</option>
        </select>
      </div>
      <div class="flex justify-between">
        <button type="button" class="text-sm text-[var(--muted)]" @click="step = 4">Back</button>
        <button type="button" class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white" @click="saveProgress(6)">
          Continue
        </button>
      </div>
    </div>

    <!-- Step 6: Test cases -->
    <div v-else-if="step === 6" class="space-y-4 rounded-xl border border-[var(--border)] bg-white p-6">
      <p class="text-sm text-[var(--muted)]">Starter evaluation cases from your template (read-only draft for Phase 6).</p>
      <ul v-if="starterCases.length" class="space-y-2 text-sm">
        <li v-for="c in starterCases" :key="c.name" class="flex items-center gap-2">
          <input type="checkbox" checked disabled />
          {{ c.name }}
        </li>
      </ul>
      <p v-else class="text-sm text-[var(--muted)]">No starter cases yet. You can add datasets in Phase 6.</p>
      <div class="flex justify-between">
        <button type="button" class="text-sm text-[var(--muted)]" @click="step = 5">Back</button>
        <button type="button" class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white" @click="saveProgress(7)">
          Continue
        </button>
      </div>
    </div>

    <!-- Step 7: Playground -->
    <div v-else-if="step === 7" class="space-y-4 rounded-xl border border-[var(--border)] bg-white p-6">
      <p class="text-[var(--muted)]">Interactive playground arrives in Phase 3. Try the stub with a suggested first question.</p>
      <NuxtLink
        to="/playground"
        class="inline-block rounded-lg border border-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent)]"
      >
        Open playground stub
      </NuxtLink>
      <div class="flex justify-between">
        <button type="button" class="text-sm text-[var(--muted)]" @click="step = 6">Back</button>
        <button type="button" class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white" @click="saveProgress(8)">
          Continue
        </button>
      </div>
    </div>

    <!-- Step 8: Evaluation -->
    <div v-else-if="step === 8" class="space-y-4 rounded-xl border border-[var(--border)] bg-white p-6">
      <p class="text-[var(--muted)]">We recommend running a Quick Check evaluation once Phase 6 is available.</p>
      <NuxtLink to="/evaluations" class="text-sm text-[var(--accent)] hover:underline">View evaluations stub →</NuxtLink>
      <div class="flex justify-between">
        <button type="button" class="text-sm text-[var(--muted)]" @click="step = 7">Back</button>
        <button
          type="button"
          class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white"
          :disabled="saving"
          @click="complete"
        >
          Complete onboarding
        </button>
      </div>
    </div>
  </div>
</template>
