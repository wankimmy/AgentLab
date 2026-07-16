<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface Template {
  id: string
  slug: string
  name: string
  description: string
  risk_level: string
}

const { api } = useApi()
const templates = ref<Template[]>([])
const name = ref('')
const selectedTemplate = ref<string | null>(null)
const error = ref('')
const loading = ref(false)

onMounted(async () => {
  templates.value = await api<Template[]>('/templates')
})

async function createAgent() {
  if (!name.value.trim()) {
    error.value = 'Agent name is required'
    return
  }
  error.value = ''
  loading.value = true
  try {
    const body: Record<string, unknown> = { name: name.value }
    if (selectedTemplate.value) {
      body.template_id = selectedTemplate.value
    }
    const agent = await api<{ id: string }>('/agents', {
      method: 'POST',
      body: JSON.stringify(body),
    })
    await navigateTo(`/agents/${agent.id}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to create agent'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <h1 class="text-3xl font-semibold">Create Agent</h1>
    <p class="mt-1 text-[var(--muted)]">Start from a template or empty configuration</p>

    <form class="mt-8 space-y-6" @submit.prevent="createAgent">
      <div>
        <label class="mb-1 block text-sm text-[var(--muted)]" for="name">Agent name</label>
        <input
          id="name"
          v-model="name"
          type="text"
          required
          class="w-full rounded-lg border border-[var(--border)] px-3 py-2"
          placeholder="ERP Support Assistant"
        />
      </div>

      <div>
        <label class="mb-2 block text-sm text-[var(--muted)]">Template (optional)</label>
        <div class="space-y-2">
          <label class="flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--border)] bg-white p-3">
            <input v-model="selectedTemplate" type="radio" :value="null" />
            <span>
              <span class="font-medium">Start from empty</span>
              <span class="mt-0.5 block text-sm text-[var(--muted)]">Blank configuration</span>
            </span>
          </label>
          <label
            v-for="tpl in templates"
            :key="tpl.id"
            class="flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--border)] bg-white p-3"
          >
            <input v-model="selectedTemplate" type="radio" :value="tpl.id" />
            <span>
              <span class="font-medium">{{ tpl.name }}</span>
              <span class="mt-0.5 block text-sm text-[var(--muted)]">{{ tpl.description }}</span>
            </span>
          </label>
        </div>
      </div>

      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

      <button
        type="submit"
        class="rounded-lg bg-[var(--accent)] px-4 py-2.5 font-medium text-white hover:bg-[var(--accent-hover)]"
        :disabled="loading"
      >
        {{ loading ? 'Creating...' : 'Create Agent' }}
      </button>
    </form>
  </div>
</template>
