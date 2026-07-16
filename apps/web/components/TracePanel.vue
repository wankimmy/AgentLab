<script setup lang="ts">
export interface Citation {
  document_id: string
  document_name: string
  chunk_id: string
  page_number?: number | null
  heading?: string | null
  excerpt: string
  score?: number
}

export interface ToolTraceItem {
  tool: string
  arguments?: Record<string, unknown>
  status?: string
  output?: unknown
}

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
  retrieved_chunks?: Citation[]
  tool_requests?: ToolTraceItem[]
  tool_results?: ToolTraceItem[]
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
      <div v-if="trace.tool_requests?.length">
        <p class="text-xs text-[var(--muted)]">Tool requests ({{ trace.tool_requests.length }})</p>
        <ul class="mt-2 space-y-2">
          <li
            v-for="(req, i) in trace.tool_requests"
            :key="i"
            class="rounded-lg bg-slate-50 p-2 text-xs"
          >
            <p class="font-medium">{{ req.tool }}</p>
            <pre class="mono mt-1 overflow-x-auto">{{ JSON.stringify(req.arguments, null, 2) }}</pre>
          </li>
        </ul>
      </div>
      <div v-if="trace.tool_results?.length">
        <p class="text-xs text-[var(--muted)]">Tool results ({{ trace.tool_results.length }})</p>
        <ul class="mt-2 space-y-2">
          <li
            v-for="(res, i) in trace.tool_results"
            :key="i"
            class="rounded-lg bg-slate-50 p-2 text-xs"
          >
            <p class="font-medium">{{ res.tool }} · {{ res.status }}</p>
            <pre class="mono mt-1 overflow-x-auto">{{ JSON.stringify(res.output, null, 2) }}</pre>
          </li>
        </ul>
      </div>
      <div v-if="trace.retrieved_chunks?.length">
        <p class="text-xs text-[var(--muted)]">Retrieved chunks ({{ trace.retrieved_chunks.length }})</p>
        <ul class="mt-2 space-y-2">
          <li
            v-for="c in trace.retrieved_chunks"
            :key="c.chunk_id"
            class="rounded-lg bg-slate-50 p-2 text-xs"
          >
            <p class="font-medium">{{ c.document_name }}</p>
            <p v-if="c.heading" class="text-[var(--muted)]">{{ c.heading }}</p>
            <p class="mt-1">{{ c.excerpt }}</p>
          </li>
        </ul>
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
