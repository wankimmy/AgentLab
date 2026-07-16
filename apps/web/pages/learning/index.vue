<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

interface Guide {
  id: string
  slug: string
  title: string
  section: string
  summary: string
}

const { api } = useApi()
const guides = ref<Guide[]>([])

const sections = computed(() => {
  const grouped: Record<string, Guide[]> = {}
  for (const g of guides.value) {
    if (!grouped[g.section]) {
      grouped[g.section] = []
    }
    grouped[g.section]!.push(g)
  }
  return grouped
})

onMounted(async () => {
  guides.value = await api<Guide[]>('/guides')
})
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-3xl font-semibold">Learning centre</h1>
      <p class="mt-1 text-[var(--muted)]">Foundation guides for building and evaluating agents</p>
    </div>

    <div v-for="(items, section) in sections" :key="section" class="mb-8">
      <h2 class="mb-3 text-lg font-medium capitalize">{{ section }}</h2>
      <div class="space-y-3">
        <NuxtLink
          v-for="guide in items"
          :key="guide.id"
          :to="`/learning/${guide.slug}`"
          class="block rounded-xl border border-[var(--border)] bg-white p-5 hover:border-[var(--accent)]"
        >
          <h3 class="font-medium">{{ guide.title }}</h3>
          <p class="mt-1 text-sm text-[var(--muted)]">{{ guide.summary }}</p>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
