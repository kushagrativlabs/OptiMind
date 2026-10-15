import { FormEvent, useEffect, useRef, useState } from 'react'
import {
  ChatMessage,
  ConversationSummary,
  deleteConversation,
  getConversation,
  getConversations,
  getModels,
  getSystemStatus,
  OllamaModel,
  streamChat,
  ServiceState,
  SystemStatus,
} from './services/api'

const initialMessage: ChatMessage = {
  role: 'assistant',
  content:
    "Hello — I’m OptiMind. Once Ollama is online, I can help you plan and improve your websites while keeping every action under your control.",
}

const StatusPill = ({ label, service }: { label: string; service?: ServiceState }) => (
  <div className="status-pill" title={service?.detail ?? 'Checking connection'}>
    <span className={`status-dot ${service?.status ?? 'checking'}`} />
    <span>{label}</span>
  </div>
)

const MessageText = ({ content }: { content: string }) => {
  const pattern = /(\[[^\]]+\]\(https?:\/\/[^)]+\)|https?:\/\/[^\s]+)/g
  return (
    <p>
      {content.split(pattern).map((part, index) => {
        const markdownLink = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/)
        const plainUrl = part.match(/^https?:\/\/[^\s]+$/)
        if (markdownLink) {
          return (
            <a href={markdownLink[2]} key={`${markdownLink[2]}-${index}`} rel="noreferrer" target="_blank">
              {markdownLink[1]}
            </a>
          )
        }
        if (plainUrl) {
          return (
            <a href={part} key={`${part}-${index}`} rel="noreferrer" target="_blank">
              {part}
            </a>
          )
        }
        return part
      })}
    </p>
  )
}

function App() {
  const [webSearchPreference] = useState(
    () => localStorage.getItem('optimind-web-search'),
  )
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [models, setModels] = useState<OllamaModel[]>([])
  const [selectedModel, setSelectedModel] = useState(
    () => localStorage.getItem('optimind-model') ?? 'qwen2.5:3b',
  )
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage])
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [deletingConversationId, setDeletingConversationId] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [webSearch, setWebSearch] = useState(
    () => webSearchPreference === 'true',
  )
  const [error, setError] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const refreshStatus = async () => {
    try {
      setStatus(await getSystemStatus())
    } catch {
      setStatus(null)
    }
  }

  const refreshConversations = async () => {
    try {
      setConversations(await getConversations())
    } catch {
      setConversations([])
    }
  }

  useEffect(() => {
    let active = true

    Promise.all([getSystemStatus(), getModels()])
      .then(([nextStatus, availableModels]) => {
        if (!active) return

        setStatus(nextStatus)
        setModels(availableModels)
        if (nextStatus.web_search.status !== 'online') {
          setWebSearch(false)
        } else if (webSearchPreference === null) {
          setWebSearch(nextStatus.web_search.status === 'online')
        }
        setSelectedModel((current) => {
          const isAvailable = availableModels.some((model) => model.name === current)
          if (isAvailable) return current

          const configured = availableModels.find(
            (model) => model.name === nextStatus.ollama.model,
          )
          return configured?.name ?? availableModels[0]?.name ?? current
        })
      })
      .catch(() => {
        if (active) setStatus(null)
      })

    return () => {
      active = false
    }
  }, [webSearchPreference])

  useEffect(() => {
    let active = true

    getConversations()
      .then((savedConversations) => {
        if (active) setConversations(savedConversations)
      })
      .catch(() => {
        if (active) setConversations([])
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('optimind-model', selectedModel)
  }, [selectedModel])

  useEffect(() => {
    localStorage.setItem('optimind-web-search', String(webSearch))
  }, [webSearch])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const startConversation = () => {
    setConversationId(null)
    setMessages([initialMessage])
    setDraft('')
    setError(null)
  }

  const openConversation = async (id: string) => {
    if (isSending) return
    setError(null)

    try {
      const conversation = await getConversation(id)
      setConversationId(conversation.id)
      setSelectedModel(conversation.model)
      setMessages([initialMessage, ...conversation.messages])
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Could not load that conversation.',
      )
    }
  }

  const removeConversation = async (conversation: ConversationSummary) => {
    if (isSending || deletingConversationId) return
    if (!window.confirm(`Delete “${conversation.title}”? This cannot be undone.`)) return

    setDeletingConversationId(conversation.id)
    setError(null)
    try {
      await deleteConversation(conversation.id)
      setConversations((current) =>
        current.filter((item) => item.id !== conversation.id),
      )
      if (conversation.id === conversationId) startConversation()
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Could not delete that conversation.',
      )
    } finally {
      setDeletingConversationId(null)
    }
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const content = draft.trim()
    if (!content || isSending) return

    const nextMessages = [...messages, { role: 'user' as const, content }]
    setMessages(nextMessages)
    setDraft('')
    setError(null)
    setIsSending(true)
    setIsStreaming(false)

    try {
      await streamChat(
        nextMessages.slice(1),
        selectedModel,
        conversationId,
        webSearch,
        {
          onConversation: (nextConversationId) => {
            setConversationId(nextConversationId)
          },
          onToken: (chunk) => {
            setIsStreaming(true)
            setMessages((current) => {
              const lastMessage = current.at(-1)
              if (lastMessage?.role === 'assistant') {
                return [
                  ...current.slice(0, -1),
                  { ...lastMessage, content: lastMessage.content + chunk },
                ]
              }
              return [...current, { role: 'assistant', content: chunk }]
            })
          },
        },
      )
      await refreshConversations()
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'OptiMind could not complete that request.',
      )
      await refreshStatus()
    } finally {
      setIsSending(false)
      setIsStreaming(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <div>
            <strong>OptiMind</strong>
            <small>Local AI workspace</small>
          </div>
        </div>

        <button className="new-chat" onClick={startConversation}>
          <span>＋</span> New conversation
        </button>

        <nav aria-label="Workspace">
          <p className="nav-label">Workspace</p>
          <a className="nav-item active" href="#conversation">
            <span>◌</span> Conversation
          </a>
          <a className="nav-item disabled" href="#websites" aria-disabled="true">
            <span>◇</span> Websites <small>Phase 3</small>
          </a>
          <a className="nav-item disabled" href="#audits" aria-disabled="true">
            <span>⌁</span> Audits <small>Phase 4</small>
          </a>
        </nav>

        <section className="history" aria-label="Conversation history">
          <p className="nav-label">History</p>
          {conversations.length === 0 ? (
            <p className="history-empty">No saved conversations yet</p>
          ) : (
            <div className="history-list">
              {conversations.map((conversation) => (
                <div
                  className={`history-item ${conversation.id === conversationId ? 'active' : ''}`}
                  key={conversation.id}
                >
                  <button
                    className="history-open"
                    disabled={isSending || deletingConversationId === conversation.id}
                    onClick={() => void openConversation(conversation.id)}
                    title={conversation.title}
                  >
                    <span>{conversation.title}</span>
                    <small>{conversation.model}</small>
                  </button>
                  <button
                    aria-label={`Delete ${conversation.title}`}
                    className="history-delete"
                    disabled={isSending || deletingConversationId !== null}
                    onClick={() => void removeConversation(conversation)}
                    title="Delete conversation"
                  >
                    {deletingConversationId === conversation.id ? '…' : '×'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="sidebar-footer">
          <p className="nav-label">Local services</p>
          <StatusPill label="API" service={status?.api} />
          <StatusPill label="PostgreSQL" service={status?.database} />
          <StatusPill label="Ollama" service={status?.ollama} />
          <StatusPill label="Web Search" service={status?.web_search} />
          <button className="refresh-button" onClick={() => void refreshStatus()}>
            Refresh connections
          </button>
        </div>
      </aside>

      <main className="main" id="conversation">
        <header className="topbar">
          <div>
            <p className="eyebrow">PRIVATE WORKSPACE</p>
            <h1>Website growth assistant</h1>
          </div>
          <div className="topbar-actions">
            <label
              className={`web-search-toggle ${webSearch ? 'active' : ''}`}
              title={status?.web_search.detail ?? 'Checking web search'}
            >
              <input
                checked={webSearch}
                disabled={status?.web_search.status !== 'online' || isSending}
                onChange={(event) => setWebSearch(event.target.checked)}
                type="checkbox"
              />
              <span className={`status-dot ${status?.web_search.status ?? 'checking'}`} />
              <span>Web search</span>
            </label>
            <label className="model-picker">
              <span className={`status-dot ${status?.ollama.status ?? 'checking'}`} />
              <span className="model-label">Model</span>
              <select
                aria-label="AI model"
                disabled={models.length === 0 || isSending}
                onChange={(event) => setSelectedModel(event.target.value)}
                value={selectedModel}
              >
                {models.length === 0 ? (
                  <option value={selectedModel}>{selectedModel}</option>
                ) : (
                  models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))
                )}
              </select>
              <span className="select-chevron" aria-hidden="true">⌄</span>
            </label>
          </div>
        </header>

        <section className="conversation" aria-live="polite">
          <div className="messages">
            {messages.map((message, index) => (
              <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                <div className="avatar">{message.role === 'assistant' ? 'O' : 'Y'}</div>
                <div>
                  <p className="message-author">
                    {message.role === 'assistant' ? 'OptiMind' : 'You'}
                  </p>
                  <MessageText content={message.content} />
                </div>
              </article>
            ))}
            {isSending && !isStreaming && (
              <article className="message assistant">
                <div className="avatar">O</div>
                <div>
                  <p className="message-author">OptiMind</p>
                  <div className="thinking" aria-label="Thinking">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </article>
            )}
            <div ref={endRef} />
          </div>

          <div className="composer-wrap">
            {error && <div className="error-banner">{error}</div>}
            <form className="composer" onSubmit={submit}>
              <textarea
                aria-label="Message OptiMind"
                disabled={isSending}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    event.currentTarget.form?.requestSubmit()
                  }
                }}
                placeholder="Ask OptiMind about a website…"
                rows={1}
                value={draft}
              />
              <button disabled={!draft.trim() || isSending} type="submit">
                <span>Send</span> ↑
              </button>
            </form>
            <p className="composer-note">
              {webSearch ? 'Web search on · Current sources will be cited' : 'Local-first · Web search off'}
            </p>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App

