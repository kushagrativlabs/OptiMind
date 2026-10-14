export type ServiceState = {
  status: 'online' | 'offline'
  detail: string
}

export type SystemStatus = {
  api: ServiceState
  database: ServiceState
  ollama: ServiceState & { model: string }
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

export type OllamaModel = {
  name: string
  size: number
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

export const sendChat = (
  messages: ChatMessage[],
  model: string,
  conversationId: string | null,
) =>
  request<{ message: ChatMessage; model: string; conversation_id: string }>(
    '/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      model,
      conversation_id: conversationId,
    }),
  },
  )

