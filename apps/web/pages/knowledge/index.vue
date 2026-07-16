<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })
</script>

<template>
  <div>
    <h1 class="text-3xl font-semibold">Knowledge</h1>
    <p class="mt-1 text-[var(--muted)]">Document collections and RAG configuration — Phase 4</p>

    <div class="mt-8 grid gap-6 lg:grid-cols-3">
      <div class="lg:col-span-2">
        <EmptyState
          title="No knowledge collections yet"
          description="Upload approved documents to ground your agent answers. Coming in Phase 4."
          :actions="[
            { label: 'Read RAG guide', to: '/learning/what-is-rag' },
            { label: 'Back to agents', to: '/agents' },
          ]"
        />
      </div>
      <HelpPanel
        title="Knowledge collections"
        why="RAG retrieves relevant document chunks before the model answers."
        :needs="['Approved PDFs or markdown', 'Sensitive data removed', 'Collection linked to agent']"
        :steps="['Create collection', 'Upload documents', 'Link to agent version', 'Test citations']"
        :mistakes="['Uploading draft policies', 'Mixing unrelated domains in one collection']"
        :next-action="{ label: 'Prepare knowledge guide', to: '/learning/how-to-prepare-knowledge' }"
      />
    </div>
  </div>
</template>
