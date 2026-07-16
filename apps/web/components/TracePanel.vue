<script setup lang="ts">
export interface TraceData {
  id: string
  provider: string
  model: string
  duration_ms: number
  ttft_ms: number | null
  input_tokens: number
  output_tokens: number
  estimated_cost: number
  overrides: Record<string, unknown>
  events: Array<{ event_type: string; payload: Record<string, unknown> }>
}

defineProps<{
  trace: TraceData | null
  loading: boolean
}>()
</script>

<template>
  <div class="rounded-xl border border-[var(--border)] bg-white p-4 text-sm">
    <h2 class="font-medium">Trace</h2>
    <p v-if="loading" class="mt-4 text-[var(--muted)]">Loading trace...</p>
    <p v-else-if="!trace" class="mt-4 text-[var(--muted)]">Send a message to see trace details.</p>
    <div v-else class="mt-4 space-y-3">
      <div class="grid grid-cols-2 gap-2">
        <div>
          <p class="text-xs text-[var(--muted)]">Duration</p>
          <p class="font-medium">{{ trace.duration_ms }} ms</p>
        </div>
        <div>
          <p class="text-xs text-[var(--muted)]">TTFT</p>
          <p class="font-medium">{{ trace.ttft_ms ?? '—' }} ms</p>
        </div>
        <div>
          <p class="text-xs text-[var(--muted)]">Input tokens</p>
          <p class="font-medium">{{ trace.input_tokens }}</p>
        </div>
        <div>
          <p class="text-xs text-[var(--muted)]">Output tokens</p>
          <p class="font-medium">{{ trace.output_tokens }}</p>
        </div>
        <div class="col-span-2">
          <p class="text-xs text-[var(--muted)]">Estimated cost</p>
          <p class="font-medium">${{ trace.estimated_cost.toFixed(6) }}</p>
        </div>
      </div>
      <div>
        <p class="text-xs text-[var(--muted)]">Provider / model</p>
        <p>{{ trace.provider }} / {{ trace.model }}</p>
      </div>
      <div v-if="Object.keys(trace.overrides).length">
        <p class="text-xs text-[var(--muted)]">Overrides applied</p>
        <pre class="mono mt-1 rounded bg-slate-50 p-2 text-xs">{{ JSON.stringify(trace.overrides, null, 2) }}</pre>
      </div>
      <div v-if="trace.events.length">
        <p class="text-xs text-[var(--muted)]">Events ({{ trace.events.length }})</p>
        <ul class="mt-1 max-h-40 space-y-1 overflow-y-auto text-xs text-[var(--muted)]">
          <li v-for="(evt, i) in trace.events" :key="i">{{ evt.event_type }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>
