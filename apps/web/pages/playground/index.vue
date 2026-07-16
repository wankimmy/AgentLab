<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })
</script>

<template>
  <div>
    <h1 class="text-3xl font-semibold">Playground</h1>
    <p class="mt-1 text-[var(--muted)]">Interactive agent testing — Phase 3</p>

    <div class="mt-8 grid gap-6 lg:grid-cols-3">
      <div class="lg:col-span-2">
        <EmptyState
          title="Playground coming in Phase 3"
          description="You will stream test messages, inspect tool calls, and compare versions here."
          :actions="[
            { label: 'Continue onboarding', to: '/onboarding', primary: true },
            { label: 'View agents', to: '/agents' },
          ]"
        />
        <p class="mt-4 text-sm text-[var(--muted)]">
          Suggested first question: “How do I create a purchase requisition?”
        </p>
      </div>
      <HelpPanel
        title="Using the playground"
        why="Manual testing catches issues before formal evaluation runs."
        :steps="['Select agent version', 'Send a realistic user message', 'Check citations and refusals']"
        :verify="['Unsupported questions are refused', 'Tool calls match configuration']"
      />
    </div>
  </div>
</template>
