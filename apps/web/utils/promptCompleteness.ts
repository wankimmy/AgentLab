export interface CompletenessItem {
  id: string
  label: string
  met: boolean
}

const SECTION_PATTERNS: Record<string, RegExp> = {
  role: /\bROLE\b/i,
  objective: /\bPRIMARY OBJECTIVE\b|\bOBJECTIVE\b/i,
  prohibited: /\bPROHIBITED\b/i,
  uncertainty: /\bWHEN INFORMATION IS MISSING\b|\bMISSING\b/i,
  citations: /\bCITATIONS?\b/i,
}

export function checkPromptCompleteness(prompt: string): CompletenessItem[] {
  const role = SECTION_PATTERNS.role!
  const objective = SECTION_PATTERNS.objective!
  const prohibited = SECTION_PATTERNS.prohibited!
  const uncertainty = SECTION_PATTERNS.uncertainty!
  const citations = SECTION_PATTERNS.citations!
  return [
    { id: 'role', label: 'Role defined', met: role.test(prompt) },
    { id: 'objective', label: 'Objective stated', met: objective.test(prompt) },
    { id: 'prohibited', label: 'Prohibited behaviour listed', met: prohibited.test(prompt) },
    { id: 'uncertainty', label: 'Missing-info handling', met: uncertainty.test(prompt) },
    { id: 'citations', label: 'Citation rules included', met: citations.test(prompt) },
  ]
}

export function completenessScore(items: CompletenessItem[]): number {
  if (!items.length) return 0
  return Math.round((items.filter((i) => i.met).length / items.length) * 100)
}
