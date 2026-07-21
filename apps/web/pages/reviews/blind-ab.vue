<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const { api } = useApi()

const leftMessageId = ref('')
const rightMessageId = ref('')
const leftPreview = ref('')
const rightPreview = ref('')
const preference = ref<'left' | 'right' | ''>('')
const revealed = ref<Record<string, string> | null>(null)
const submitting = ref(false)

async function submit() {
  if (!leftMessageId.value || !rightMessageId.value || !preference.value) return
  submitting.value = true
  try {
    const res = await api<{
      preference: string
      revealed_labels: Record<string, string>
    }>('/reviews/blind-ab', {
      method: 'POST',
      body: JSON.stringify({
        left_message_id: leftMessageId.value,
        right_message_id: rightMessageId.value,
        preference: preference.value,
      }),
    })
    revealed.value = res.revealed_labels
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <NuxtLink to="/evaluations" class="text-sm text-[var(--accent)]">← Evaluations</NuxtLink>
    <h1 class="mt-2 text-2xl font-semibold">Blind A/B review</h1>
    <p class="mt-1 text-sm text-[var(--muted)]">
      Compare two assistant answers without seeing version labels until you submit a preference.
    </p>

    <div class="mt-8 space-y-4">
      <label class="block text-sm">
        <span class="font-medium">Left message ID</span>
        <input v-model="leftMessageId" class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs">
      </label>
      <label class="block text-sm">
        <span class="font-medium">Right message ID</span>
        <input v-model="rightMessageId" class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs">
      </label>
      <label class="block text-sm">
        <span class="font-medium">Answer A (paste preview)</span>
        <textarea v-model="leftPreview" class="mt-1 w-full rounded border px-3 py-2" rows="4" />
      </label>
      <label class="block text-sm">
        <span class="font-medium">Answer B (paste preview)</span>
        <textarea v-model="rightPreview" class="mt-1 w-full rounded border px-3 py-2" rows="4" />
      </label>

      <div class="flex gap-4">
        <button
          type="button"
          class="flex-1 rounded-lg border-2 px-4 py-3 text-left"
          :class="preference === 'left' ? 'border-[var(--accent)]' : 'border-[var(--border)]'"
          @click="preference = 'left'"
        >
          <span class="text-xs font-medium text-[var(--muted)]">Option A</span>
          <p class="mt-1 text-sm whitespace-pre-wrap">{{ leftPreview || '—' }}</p>
        </button>
        <button
          type="button"
          class="flex-1 rounded-lg border-2 px-4 py-3 text-left"
          :class="preference === 'right' ? 'border-[var(--accent)]' : 'border-[var(--border)]'"
          @click="preference = 'right'"
        >
          <span class="text-xs font-medium text-[var(--muted)]">Option B</span>
          <p class="mt-1 text-sm whitespace-pre-wrap">{{ rightPreview || '—' }}</p>
        </button>
      </div>

      <button
        type="button"
        class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        :disabled="submitting || !preference"
        @click="submit"
      >
        {{ submitting ? 'Submitting...' : 'Submit preference & reveal labels' }}
      </button>

      <div v-if="revealed" class="rounded-lg border border-green-200 bg-green-50 p-4 text-sm">
        <p class="font-medium">Labels revealed</p>
        <p class="mt-1">Option A was: {{ revealed.left }}</p>
        <p>Option B was: {{ revealed.right }}</p>
      </div>
    </div>
  </div>
</template>
