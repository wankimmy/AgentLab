<script setup lang="ts">
export interface EmptyAction {
  label: string
  to?: string
  onClick?: () => void
  primary?: boolean
}

defineProps<{
  title: string
  description: string
  actions?: EmptyAction[]
}>()
</script>

<template>
  <div class="rounded-xl border border-dashed border-[var(--border)] bg-white/60 p-8 text-center">
    <h2 class="text-lg font-medium">{{ title }}</h2>
    <p class="mt-2 text-[var(--muted)]">{{ description }}</p>
    <div v-if="actions?.length" class="mt-6 flex flex-wrap justify-center gap-3">
      <template v-for="action in actions" :key="action.label">
        <NuxtLink
          v-if="action.to"
          :to="action.to"
          class="rounded-lg px-4 py-2 text-sm font-medium"
          :class="
            action.primary
              ? 'bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]'
              : 'border border-[var(--accent)] text-[var(--accent)] hover:bg-teal-50'
          "
        >
          {{ action.label }}
        </NuxtLink>
        <button
          v-else
          type="button"
          class="rounded-lg px-4 py-2 text-sm font-medium"
          :class="
            action.primary
              ? 'bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]'
              : 'border border-[var(--accent)] text-[var(--accent)] hover:bg-teal-50'
          "
          @click="action.onClick?.()"
        >
          {{ action.label }}
        </button>
      </template>
    </div>
  </div>
</template>
