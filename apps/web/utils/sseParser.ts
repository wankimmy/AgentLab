export interface SSEEvent {
  event: string
  data: Record<string, unknown>
}

export function parseSSEChunk(buffer: string): { events: SSEEvent[]; remainder: string } {
  const events: SSEEvent[] = []
  const parts = buffer.split('\n\n')
  const remainder = parts.pop() || ''
  for (const part of parts) {
    if (!part.trim()) continue
    let event = 'message'
    let dataStr = ''
    for (const line of part.split('\n')) {
      if (line.startsWith('event: ')) event = line.slice(7).trim()
      if (line.startsWith('data: ')) dataStr = line.slice(6)
    }
    if (dataStr) {
      try {
        events.push({ event, data: JSON.parse(dataStr) as Record<string, unknown> })
      } catch {
        events.push({ event, data: { raw: dataStr } })
      }
    }
  }
  return { events, remainder }
}
