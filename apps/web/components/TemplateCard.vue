<script setup lang="ts">
defineProps<{
  id: string
  slug: string
  name: string
  description: string
  risk_level: string
  setup_effort: string
}>()

const riskClass: Record<string, string> = {
  low: 'bg-emerald-100 text-emerald-800',
  medium: 'bg-amber-100 text-amber-800',
  high: 'bg-red-100 text-red-800',
}
</script>

<template>
  <NuxtLink
    :to="`/templates/${id}`"
    class="block rounded-xl border border-[var(--border)] bg-white p-5 transition hover:border-[var(--accent)]"
  >
    <div class="flex items-start justify-between gap-3">
      <div>
        <h2 class="font-medium">{{ name }}</h2>
        <p class="mt-1 text-sm text-[var(--muted)] line-clamp-2">{{ description }}</p>
        <p class="mt-2 text-xs text-[var(--muted)]">Setup: {{ setup_effort }}</p>
      </div>
      <span class="shrink-0 rounded px-2 py-0.5 text-xs font-medium" :class="riskClass[risk_level] || riskClass.low">
        {{ risk_level }} risk
      </span>
    </div>
  </NuxtLink>
</template>
