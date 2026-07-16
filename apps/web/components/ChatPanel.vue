<script setup lang="ts">
export interface ChatMessage {
  id: string
  role: string
  content: string
  trace_id?: string | null
  feedback_rating?: number | null
}

const props = defineProps<{
  messages: ChatMessage[]
  streaming: boolean
  streamingContent: string
}>()

const emit = defineEmits<{
  send: [content: string]
  feedback: [messageId: string, rating: number, notes: string]
}>()

const input = ref('')
const feedbackNotes = ref<Record<string, string>>({})

function submit() {
  if (!input.value.trim() || props.streaming) return
  emit('send', input.value.trim())
  input.value = ''
}

function rate(messageId: string, rating: number) {
  emit('feedback', messageId, rating, feedbackNotes.value[messageId] || '')
}
</script>

<template>
  <div class="flex h-[min(70vh,640px)] flex-col rounded-xl border border-[var(--border)] bg-white">
    <div class="flex-1 space-y-3 overflow-y-auto p-4">
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="rounded-lg px-3 py-2 text-sm"
        :class="msg.role === 'user' ? 'ml-8 bg-slate-100' : 'mr-8 bg-teal-50'"
      >
        <p class="mb-1 text-xs font-medium uppercase text-[var(--muted)]">{{ msg.role }}</p>
        <p class="whitespace-pre-wrap">{{ msg.content }}</p>
        <div v-if="msg.role === 'assistant'" class="mt-2 flex items-center gap-2 text-xs">
          <span class="text-[var(--muted)]">Rate:</span>
          <button
            v-for="n in 5"
            :key="n"
            type="button"
            class="rounded px-1"
            :class="msg.feedback_rating === n ? 'bg-[var(--accent)] text-white' : 'hover:bg-slate-200'"
            @click="rate(msg.id, n)"
          >
            {{ n }}
          </button>
        </div>
      </div>
      <div v-if="streaming" class="mr-8 rounded-lg bg-teal-50 px-3 py-2 text-sm">
        <p class="mb-1 text-xs font-medium uppercase text-[var(--muted)]">assistant</p>
        <p class="whitespace-pre-wrap">{{ streamingContent }}<span class="animate-pulse">▌</span></p>
      </div>
    </div>
    <form class="border-t border-[var(--border)] p-3" @submit.prevent="submit">
      <div class="flex gap-2">
        <input
          v-model="input"
          type="text"
          placeholder="Type a message..."
          class="flex-1 rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
          :disabled="streaming"
        >
        <button
          type="submit"
          class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          :disabled="streaming || !input.trim()"
        >
          Send
        </button>
      </div>
    </form>
  </div>
</template>
