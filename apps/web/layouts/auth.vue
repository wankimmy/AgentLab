<template>
  <div class="flex min-h-screen items-center justify-center px-6">
    <div class="w-full max-w-md">
      <div class="mb-8 text-center">
        <h1 class="text-4xl font-semibold tracking-tight text-[var(--accent)]">AgentLab</h1>
        <p class="mt-2 text-[var(--muted)]">AI agent playground and evaluation platform</p>
      </div>
      <div class="rounded-2xl border border-[var(--border)] bg-white p-8 shadow-sm">
        <slot />
      </div>
    </div>
  </div>
</template>
