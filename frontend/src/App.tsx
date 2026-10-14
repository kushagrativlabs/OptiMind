import { FormEvent, useEffect, useRef, useState } from 'react'
import {
  ChatMessage,
  getModels,
  getSystemStatus,
  OllamaModel,
  sendChat,
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

function App() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [models, setModels] = useState<OllamaModel[]>([])
  const [selectedModel, setSelectedModel] = useState(
    () => localStorage.getItem('optimind-model') ?? 'qwen2.5:3b',
  )
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage])
  const [draft, setDraft] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const refreshStatus = async () => {
    try {
      setStatus(await getSystemStatus())
    } catch {
      setStatus(null)
    }
  }

  useEffect(() => {
    let active = true

    Promise.all([getSystemStatus(), getModels()])
      .then(([nextStatus, availableModels]) => {
        if (!active) return

        setStatus(nextStatus)
        setModels(availableModels)
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
  }, [])

  useEffect(() => {
    localStorage.setItem('optimind-model', selectedModel)
  }, [selectedModel])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const content = draft.trim()
    if (!content || isSending) return

    const nextMessages = [...messages, { role: 'user' as const, content }]
    setMessages(nextMessages)
    setDraft('')
    setError(null)
    setIsSending(true)

    try {
      const response = await sendChat(nextMessages.slice(1), selectedModel)
      setMessages((current) => [...current, response.message])
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'OptiMind could not complete that request.',
      )
      await refreshStatus()
    } finally {
      setIsSending(false)
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

        <button className="new-chat" onClick={() => setMessages([initialMessage])}>
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

        <div className="sidebar-footer">
          <p className="nav-label">Local services</p>
          <StatusPill label="API" service={status?.api} />
          <StatusPill label="PostgreSQL" service={status?.database} />
          <StatusPill label="Ollama" service={status?.ollama} />
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
                  <p>{message.content}</p>
                </div>
              </article>
            ))}
            {isSending && (
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
              Local-first · No website changes can be made in Phase 1
            </p>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App

