<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })
</script>

<template>
  <div>
    <h1 class="text-3xl font-semibold">Evaluations</h1>
    <p class="mt-1 text-[var(--muted)]">Quick Check and release evaluations — Phase 6</p>

    <div class="mt-8 grid gap-6 lg:grid-cols-3">
      <div class="lg:col-span-2">
        <EmptyState
          title="No evaluation runs yet"
          description="Run Quick Check against starter cases, then graduate to release evaluation."
          :actions="[
            { label: 'Evaluation guide', to: '/learning/what-is-evaluation' },
            { label: 'Browse templates', to: '/templates' },
          ]"
        />
      </div>
      <HelpPanel
        title="Evaluation workflow"
        why="Structured test cases measure correctness, groundedness, and security."
        :needs="['Evaluation dataset', 'Agent version', 'Judge rubric']"
        :steps="['Import starter pack', 'Run Quick Check', 'Review failures', 'Run release eval']"
        :mistakes="['Skipping security cases', 'No citation checks for RAG agents']"
      />
    </div>
  </div>
</template>
