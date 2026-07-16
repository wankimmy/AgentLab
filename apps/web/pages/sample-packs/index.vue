<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

interface SamplePack {
  id: string
  slug: string
  name: string
  description: string
  is_synthetic: boolean
  manifest: Record<string, unknown>
}

const { api } = useApi()
const packs = ref<SamplePack[]>([])
const installing = ref<string | null>(null)
const installed = ref<Record<string, string>>({})

onMounted(async () => {
  packs.value = await api<SamplePack[]>('/sample-packs')
})

async function install(pack: SamplePack) {
  installing.value = pack.id
  try {
    const result = await api<{ agent_id: string }>(`/sample-packs/${pack.id}/install`, { method: 'POST' })
    installed.value[pack.id] = result.agent_id
  } finally {
    installing.value = null
  }
}
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-3xl font-semibold">Sample data packs</h1>
      <p class="mt-1 text-[var(--muted)]">Install synthetic demo agents and starter content</p>
    </div>

    <div class="space-y-4">
      <div v-for="pack in packs" :key="pack.id" class="rounded-xl border border-[var(--border)] bg-white p-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="flex items-center gap-2">
              <h2 class="font-medium">{{ pack.name }}</h2>
              <span v-if="pack.is_synthetic" class="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800">SYNTHETIC</span>
            </div>
            <p class="mt-1 text-sm text-[var(--muted)]">{{ pack.description }}</p>
          </div>
          <div>
            <NuxtLink
              v-if="installed[pack.id]"
              :to="`/agents/${installed[pack.id]}`"
              class="rounded-lg border border-[var(--accent)] px-4 py-2 text-sm text-[var(--accent)]"
            >
              View agent
            </NuxtLink>
            <button
              v-else
              type="button"
              class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              :disabled="installing === pack.id"
              @click="install(pack)"
            >
              {{ installing === pack.id ? 'Installing...' : 'Install' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
