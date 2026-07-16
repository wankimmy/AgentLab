<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

interface TemplateDetail {
  id: string
  name: string
  slug: string
  description: string
  risk_level: string
  intended_use: string
  not_suitable_for: string
  system_prompt: string
  tool_config: Record<string, string>
  example_questions: string[]
  example_answers: string[]
  eval_starter_pack: { cases?: Array<{ name: string; user_message: string }> }
  common_mistakes: string[]
}

const route = useRoute()
const { api } = useApi()
const template = ref<TemplateDetail | null>(null)
const applying = ref(false)
const appliedId = ref<string | null>(null)

onMounted(async () => {
  template.value = await api<TemplateDetail>(`/templates/${route.params.id}`)
})

async function applyTemplate() {
  if (!template.value) return
  applying.value = true
  try {
    const agent = await api<{ id: string }>(`/templates/${template.value.id}/apply`, {
      method: 'POST',
      body: JSON.stringify({ name: template.value.name }),
    })
    appliedId.value = agent.id
  } finally {
    applying.value = false
  }
}
</script>

<template>
  <div v-if="template">
    <NuxtLink to="/templates" class="text-sm text-[var(--accent)]">← Back to templates</NuxtLink>
    <div class="mt-4 mb-8 flex items-end justify-between">
      <div>
        <h1 class="text-3xl font-semibold">{{ template.name }}</h1>
        <p class="mt-1 text-[var(--muted)]">{{ template.description }}</p>
      </div>
      <button
        v-if="!appliedId"
        type="button"
        class="rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
        :disabled="applying"
        @click="applyTemplate"
      >
        {{ applying ? 'Applying...' : 'Apply template' }}
      </button>
      <NuxtLink
        v-else
        :to="`/agents/${appliedId}`"
        class="rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white"
      >
        View agent →
      </NuxtLink>
    </div>

    <div class="grid gap-6 lg:grid-cols-3">
      <div class="space-y-6 lg:col-span-2">
        <section class="rounded-xl border border-[var(--border)] bg-white p-5">
          <h2 class="font-medium">System prompt</h2>
          <pre class="mono mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-xs">{{ template.system_prompt }}</pre>
        </section>
        <section class="rounded-xl border border-[var(--border)] bg-white p-5">
          <h2 class="font-medium">Example Q&A</h2>
          <div v-for="(q, i) in template.example_questions" :key="q" class="mt-3 text-sm">
            <p class="font-medium">Q: {{ q }}</p>
            <p v-if="template.example_answers[i]" class="text-[var(--muted)]">A: {{ template.example_answers[i] }}</p>
          </div>
        </section>
      </div>
      <div class="space-y-4">
        <section class="rounded-xl border border-[var(--border)] bg-white p-5 text-sm">
          <h2 class="font-medium">Intended use</h2>
          <p class="mt-2 text-[var(--muted)]">{{ template.intended_use }}</p>
          <h2 class="mt-4 font-medium">Not suitable for</h2>
          <p class="mt-2 text-[var(--muted)]">{{ template.not_suitable_for }}</p>
          <h2 class="mt-4 font-medium">Tools</h2>
          <ul class="mt-2 text-[var(--muted)]">
            <li v-for="(mode, name) in template.tool_config" :key="name">{{ name }}: {{ mode }}</li>
          </ul>
        </section>
        <HelpPanel
          title="Before you apply"
          :mistakes="template.common_mistakes"
          :verify="['Prompt includes role and prohibited behaviour', 'Tool modes match your risk level']"
        />
      </div>
    </div>
  </div>
</template>
