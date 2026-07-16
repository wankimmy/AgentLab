<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

interface GuideDetail {
  title: string
  summary: string
  screen_link: string | null
  sections: Array<{ heading: string; content: string }>
}

const route = useRoute()
const { api } = useApi()
const guide = ref<GuideDetail | null>(null)

onMounted(async () => {
  guide.value = await api<GuideDetail>(`/guides/${route.params.slug}`)
})
</script>

<template>
  <div v-if="guide">
    <NuxtLink to="/learning" class="text-sm text-[var(--accent)]">← All guides</NuxtLink>
    <h1 class="mt-4 text-3xl font-semibold">{{ guide.title }}</h1>
    <p class="mt-2 text-[var(--muted)]">{{ guide.summary }}</p>

    <article class="mt-8 space-y-6">
      <section v-for="section in guide.sections" :key="section.heading" class="rounded-xl border border-[var(--border)] bg-white p-5">
        <h2 class="font-medium">{{ section.heading }}</h2>
        <p class="mt-2 whitespace-pre-line text-sm text-[var(--muted)]">{{ section.content }}</p>
      </section>
    </article>

    <NuxtLink
      v-if="guide.screen_link"
      :to="guide.screen_link"
      class="mt-8 inline-block rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white"
    >
      Go to related screen
    </NuxtLink>
  </div>
</template>
