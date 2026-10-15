export type ServiceState = {
  status: 'online' | 'offline'
  detail: string
}

export type SystemStatus = {
  api: ServiceState
  database: ServiceState
  ollama: ServiceState & { model: string }
  image_generation: ServiceState
  web_search: ServiceState
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  images?: ChatImage[]
}

export type ChatImage = {
  name: string
  media_type: 'image/jpeg' | 'image/png' | 'image/webp'
  data: string
}

export type OllamaModel = {
  name: string
  size: number
  capabilities: string[]
}

export type ConversationSummary = {
  id: string
  title: string
  model: string
  created_at: string
  updated_at: string
}

export type ConversationDetail = ConversationSummary & {
  messages: Array<ChatMessage & { id: string; created_at: string }>
}

const request = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(path, options)

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }

  return response.json() as Promise<T>
}

export const getSystemStatus = () => request<SystemStatus>('/api/v1/status')

export const getModels = () => request<OllamaModel[]>('/api/v1/models')

export const getConversations = () =>
  request<ConversationSummary[]>('/api/v1/conversations')

export const getConversation = (conversationId: string) =>
  request<ConversationDetail>(`/api/v1/conversations/${conversationId}`)

export const deleteConversation = async (conversationId: string) => {
  const response = await fetch(`/api/v1/conversations/${conversationId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }
}

export const generateImage = (
  prompt: string,
  conversationModel: string,
  conversationId: string | null,
  signal?: AbortSignal,
) =>
  request<{ message: ChatMessage; model: string; conversation_id: string }>(
    '/api/v1/images/generate',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        conversation_id: conversationId,
        conversation_model: conversationModel,
      }),
      signal,
    },
  )

export const sendChat = (
  messages: ChatMessage[],
  model: string,
  conversationId: string | null,
  webSearch = false,
) =>
  request<{ message: ChatMessage; model: string; conversation_id: string }>(
    '/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      model,
      conversation_id: conversationId,
      web_search: webSearch,
    }),
  },
  )

type ChatStreamEvent =
  | { type: 'meta'; conversation_id: string; model: string }
  | { type: 'token'; content: string }
  | { type: 'done' }
  | { type: 'error'; detail: string }

type ChatStreamHandlers = {
  onConversation: (conversationId: string, model: string) => void
  onToken: (content: string) => void
}

export const streamChat = async (
  messages: ChatMessage[],
  model: string,
  conversationId: string | null,
  webSearch: boolean,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
) => {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      model,
      conversation_id: conversationId,
      web_search: webSearch,
    }),
    signal,
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }
  if (!response.body) throw new Error('The browser could not read the response stream.')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let tokenBuffer = ''
  let flushTimer: ReturnType<typeof setTimeout> | null = null

  const flushTokens = () => {
    if (flushTimer !== null) clearTimeout(flushTimer)
    flushTimer = null
    if (!tokenBuffer) return
    handlers.onToken(tokenBuffer)
    tokenBuffer = ''
  }

  const scheduleTokenFlush = () => {
    if (flushTimer !== null) return
    flushTimer = setTimeout(flushTokens, 32)
  }

  const processLine = (line: string) => {
    if (!line.trim()) return
    const event = JSON.parse(line) as ChatStreamEvent
    if (event.type === 'meta') {
      handlers.onConversation(event.conversation_id, event.model)
    } else if (event.type === 'token') {
      tokenBuffer += event.content
      scheduleTokenFlush()
    } else if (event.type === 'done') {
      flushTokens()
    } else if (event.type === 'error') {
      flushTokens()
      throw new Error(event.detail)
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      lines.forEach(processLine)
      if (done) break
    }
    processLine(buffer)
  } finally {
    flushTokens()
  }
}

