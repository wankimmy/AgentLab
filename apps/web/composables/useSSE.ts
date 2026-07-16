import { parseSSEChunk, type SSEEvent } from '~/utils/sseParser'

export function useSSE() {
  async function streamPost(
    path: string,
    body: unknown,
    onEvent: (event: SSEEvent) => void,
  ): Promise<void> {
    const response = await fetch(`/api/v1${path}`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || 'Stream request failed')
    }
    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parsed = parseSSEChunk(buffer)
      buffer = parsed.remainder
      for (const evt of parsed.events) onEvent(evt)
    }
    if (buffer.trim()) {
      const parsed = parseSSEChunk(`${buffer}\n\n`)
      for (const evt of parsed.events) onEvent(evt)
    }
  }

  return { streamPost }
}
