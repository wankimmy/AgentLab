import { describe, expect, it } from 'vitest'
import { checkPromptCompleteness, completenessScore } from '../utils/promptCompleteness'

describe('promptCompleteness', () => {
  it('detects structured prompt sections', () => {
    const prompt = `ROLE
You are an assistant.

PRIMARY OBJECTIVE
Help users.

PROHIBITED BEHAVIOUR
No secrets.

WHEN INFORMATION IS MISSING
Say you do not know.

CITATIONS
Cite sources.`
    const items = checkPromptCompleteness(prompt)
    expect(items.every((i) => i.met)).toBe(true)
    expect(completenessScore(items)).toBe(100)
  })

  it('scores partial prompts', () => {
    const items = checkPromptCompleteness('ROLE\nYou are helpful.')
    expect(completenessScore(items)).toBeLessThan(100)
  })
})
