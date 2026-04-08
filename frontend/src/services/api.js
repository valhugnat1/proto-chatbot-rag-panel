// API service: streaming client for the BNP chatbot backend.
//
// The backend exposes an OpenAI-compatible /v1/chat/completions endpoint
// that emits SSE chunks shaped like:
//
//     data: {"id":"...","choices":[{"delta":{"content":"Bonjour"}}]}
//     data: {"id":"...","choices":[{"delta":{"content":" !"}}]}
//     data: [DONE]

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Stream a chat completion from the backend.
 *
 * @param {Array<{role: string, content: string}>} messages - Full message history
 * @param {AbortSignal} [signal] - Optional abort signal to cancel the stream
 * @yields {string} Token deltas as they arrive
 */
export async function* streamChatCompletion(messages, signal) {
  const response = await fetch(`${API_URL}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, stream: true }),
    signal,
  })

  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`)
  }
  if (!response.body) {
    throw new Error('No response body')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // SSE events are separated by a blank line.
      let sepIndex
      while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, sepIndex)
        buffer = buffer.slice(sepIndex + 2)

        // Each event may have multiple lines; we only care about `data:` lines.
        for (const line of rawEvent.split('\n')) {
          if (!line.startsWith('data:')) continue
          const data = line.slice(5).trim()
          if (!data) continue
          if (data === '[DONE]') return

          try {
            const parsed = JSON.parse(data)
            const delta = parsed?.choices?.[0]?.delta?.content
            if (typeof delta === 'string' && delta.length > 0) {
              yield delta
            }
          } catch (err) {
            console.warn('Failed to parse SSE chunk:', data, err)
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

/**
 * Quick health check.
 */
export async function checkHealth() {
  try {
    const res = await fetch(`${API_URL}/health`)
    if (!res.ok) return { status: 'down' }
    return await res.json()
  } catch {
    return { status: 'down' }
  }
}
