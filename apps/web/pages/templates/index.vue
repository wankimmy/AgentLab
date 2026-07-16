<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

interface Template {
  id: string
  slug: string
  name: string
  description: string
  risk_level: string
  setup_effort: string
}

const { api } = useApi()
const templates = ref<Template[]>([])

onMounted(async () => {
  templates.value = await api<Template[]>('/templates')
})
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-3xl font-semibold">Templates</h1>
      <p class="mt-1 text-[var(--muted)]">Browse starter configurations for common agent types</p>
    </div>

    <HelpPanel
      class="mb-6"
      title="Choosing a template"
      why="Templates bundle prompts, tools, and evaluation starters so you can ship faster."
      :steps="['Browse templates', 'Preview prompt and tools', 'Apply to create an agent']"
      :next-action="{ label: 'Start onboarding', to: '/onboarding' }"
    />

    <div class="grid gap-4 sm:grid-cols-2">
      <TemplateCard v-for="tpl in templates" :key="tpl.id" v-bind="tpl" />
    </div>
  </div>
</template>
