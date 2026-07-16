import { describe, expect, it } from 'vitest'
import { parseSSEChunk } from '../utils/sseParser'

describe('sseParser', () => {
  it('parses token and done events', () => {
    const chunk = 'event: token\ndata: {"content":"Hello"}\n\nevent: done\ndata: {"trace_id":"abc"}\n\n'
    const { events, remainder } = parseSSEChunk(chunk)
    expect(events).toHaveLength(2)
    expect(events[0]?.event).toBe('token')
    expect(events[0]?.data.content).toBe('Hello')
    expect(events[1]?.event).toBe('done')
    expect(remainder).toBe('')
  })

  it('keeps partial chunk in remainder', () => {
    const { events, remainder } = parseSSEChunk('event: token\ndata: {"content":"Hi"}')
    expect(events).toHaveLength(0)
    expect(remainder).toContain('event: token')
  })
})
