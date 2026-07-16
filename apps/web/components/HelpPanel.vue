<script setup lang="ts">
export interface HelpPanelProps {
  title: string
  why?: string
  needs?: string[]
  steps?: string[]
  examples?: string[]
  mistakes?: string[]
  verify?: string[]
  nextAction?: { label: string; to: string }
  defaultOpen?: boolean
}

const props = withDefaults(defineProps<HelpPanelProps>(), {
  needs: () => [],
  steps: () => [],
  examples: () => [],
  mistakes: () => [],
  verify: () => [],
  defaultOpen: false,
})

const open = ref(props.defaultOpen)
</script>

<template>
  <aside class="rounded-xl border border-[var(--border)] bg-white">
    <button
      type="button"
      class="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium"
      @click="open = !open"
    >
      <span>{{ title }}</span>
      <span class="text-[var(--muted)]">{{ open ? '−' : '+' }}</span>
    </button>
    <div v-if="open" class="space-y-4 border-t border-[var(--border)] px-4 py-4 text-sm">
      <p v-if="why" class="text-[var(--muted)]">{{ why }}</p>
      <div v-if="needs.length">
        <p class="font-medium">What you need</p>
        <ul class="mt-1 list-inside list-disc text-[var(--muted)]">
          <li v-for="item in needs" :key="item">{{ item }}</li>
        </ul>
      </div>
      <div v-if="steps.length">
        <p class="font-medium">Steps</p>
        <ol class="mt-1 list-inside list-decimal text-[var(--muted)]">
          <li v-for="step in steps" :key="step">{{ step }}</li>
        </ol>
      </div>
      <div v-if="examples.length">
        <p class="font-medium">Examples</p>
        <ul class="mt-1 list-inside list-disc text-[var(--muted)]">
          <li v-for="ex in examples" :key="ex">{{ ex }}</li>
        </ul>
      </div>
      <div v-if="mistakes.length">
        <p class="font-medium">Common mistakes</p>
        <ul class="mt-1 list-inside list-disc text-[var(--muted)]">
          <li v-for="m in mistakes" :key="m">{{ m }}</li>
        </ul>
      </div>
      <div v-if="verify.length">
        <p class="font-medium">How to verify</p>
        <ul class="mt-1 list-inside list-disc text-[var(--muted)]">
          <li v-for="v in verify" :key="v">{{ v }}</li>
        </ul>
      </div>
      <NuxtLink
        v-if="nextAction"
        :to="nextAction.to"
        class="inline-block rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
      >
        {{ nextAction.label }}
      </NuxtLink>
    </div>
  </aside>
</template>
