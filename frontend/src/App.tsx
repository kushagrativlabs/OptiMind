import { FormEvent, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ChatMessage,
  ChatImage,
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

const MAX_IMAGE_BYTES = 5 * 1024 * 1024
const MAX_IMAGES = 3
const SUPPORTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

const readImage = (file: File): Promise<ChatImage> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error(`Could not read ${file.name}.`))
    reader.onload = () => {
      const result = String(reader.result)
      const data = result.split(',', 2)[1]
      if (!data) return reject(new Error(`Could not read ${file.name}.`))
      resolve({
        name: file.name,
        media_type: file.type as ChatImage['media_type'],
        data,
      })
    }
    reader.readAsDataURL(file)
  })

const MessageImages = ({ images = [] }: { images?: ChatImage[] }) => {
  if (images.length === 0) return null
  return (
    <div className="message-images">
      {images.map((image, index) => (
        <img
          alt={image.name}
          key={`${image.name}-${index}`}
          src={`data:${image.media_type};base64,${image.data}`}
        />
      ))}
    </div>
  )
}

const MessageText = ({ content }: { content: string }) => {
  return (
    <div className="message-content">
      <ReactMarkdown
        components={{
          a: ({ children, href, title }) => (
            <a href={href} rel="noreferrer" target="_blank" title={title}>
              {children}
            </a>
          ),
        }}
        remarkPlugins={[remarkGfm]}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const savedTheme = localStorage.getItem('optimind-theme')
    if (savedTheme === 'light' || savedTheme === 'dark') return savedTheme
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [models, setModels] = useState<OllamaModel[]>([])
  const [selectedModel, setSelectedModel] = useState(
    () => localStorage.getItem('optimind-model') ?? 'qwen2.5:3b',
  )
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage])
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [attachedImages, setAttachedImages] = useState<ChatImage[]>([])
  const [isSending, setIsSending] = useState(false)
  const [deletingConversationId, setDeletingConversationId] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [webSearch, setWebSearch] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedMessageIndex, setCopiedMessageIndex] = useState<number | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const activeRequestRef = useRef<AbortController | null>(null)
  const selectedModelInfo = models.find((model) => model.name === selectedModel)
  const supportsVision = selectedModelInfo?.capabilities.includes('vision') ?? false

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
  }, [])

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
    document.documentElement.dataset.theme = theme
    localStorage.setItem('optimind-theme', theme)
  }, [theme])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: isStreaming ? 'auto' : 'smooth' })
  }, [messages, isStreaming])

  useEffect(() => {
    if (!isSending) composerRef.current?.focus()
  }, [isSending])

  useEffect(() => () => activeRequestRef.current?.abort(), [])

  const startConversation = () => {
    activeRequestRef.current?.abort()
    setConversationId(null)
    setMessages([initialMessage])
    setDraft('')
    setAttachedImages([])
    setError(null)
    requestAnimationFrame(() => composerRef.current?.focus())
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
    const content = draft.trim() || (attachedImages.length > 0 ? 'Analyze the attached image.' : '')
    if (!content || isSending) return

    const nextMessages = [
      ...messages,
      { role: 'user' as const, content, images: attachedImages },
    ]
    setMessages(nextMessages)
    setDraft('')
    setAttachedImages([])
    setError(null)
    setIsSending(true)
    setIsStreaming(false)
    const controller = new AbortController()
    activeRequestRef.current = controller

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
        controller.signal,
      )
      await refreshConversations()
    } catch (requestError) {
      if (requestError instanceof Error && requestError.name === 'AbortError') {
        await refreshConversations()
        return
      }
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'OptiMind could not complete that request.',
      )
      await refreshStatus()
    } finally {
      if (activeRequestRef.current === controller) activeRequestRef.current = null
      setIsSending(false)
      setIsStreaming(false)
    }
  }

  const stopGeneration = () => {
    activeRequestRef.current?.abort()
  }

  const copyMessage = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedMessageIndex(index)
      window.setTimeout(() => {
        setCopiedMessageIndex((current) => current === index ? null : current)
      }, 1600)
    } catch {
      setError('Could not copy the reply. Please select the text and copy it manually.')
    }
  }

  const attachImages = async (files: FileList | null) => {
    if (!files) return
    const availableSlots = MAX_IMAGES - attachedImages.length
    const selectedFiles = Array.from(files).slice(0, availableSlots)
    const invalidFile = selectedFiles.find(
      (file) => !SUPPORTED_IMAGE_TYPES.includes(file.type) || file.size > MAX_IMAGE_BYTES,
    )
    if (invalidFile) {
      setError('Images must be JPEG, PNG, or WebP and no larger than 5 MB each.')
      if (imageInputRef.current) imageInputRef.current.value = ''
      return
    }

    try {
      const images = await Promise.all(selectedFiles.map(readImage))
      setAttachedImages((current) => [...current, ...images].slice(0, MAX_IMAGES))
      setError(null)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not attach the image.')
    } finally {
      if (imageInputRef.current) imageInputRef.current.value = ''
      composerRef.current?.focus()
    }
  }

  const openImagePicker = () => {
    if (!supportsVision) {
      setError('Select a vision-capable Ollama model before attaching an image.')
      return
    }
    imageInputRef.current?.click()
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
            <button
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              className="theme-toggle"
              onClick={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              type="button"
            >
              <span aria-hidden="true">{theme === 'dark' ? '☀' : '☾'}</span>
              <strong>{theme === 'dark' ? 'Light' : 'Dark'}</strong>
            </button>
            <label
              className={`web-search-toggle ${webSearch ? 'active' : ''}`}
              title={status?.web_search.detail ?? 'Checking web search'}
            >
              <input
                aria-label="Toggle web search"
                checked={webSearch}
                disabled={status?.web_search.status !== 'online' || isSending}
                onChange={(event) => setWebSearch(event.target.checked)}
                role="switch"
                type="checkbox"
              />
              <span className={`status-dot ${status?.web_search.status ?? 'checking'}`} />
              <span className="web-search-label">Web search</span>
              <span className="toggle-track" aria-hidden="true">
                <span className="toggle-thumb" />
              </span>
              <strong className="web-search-state">{webSearch ? 'On' : 'Off'}</strong>
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
                      {model.name}{model.capabilities.includes('vision') ? ' · Vision' : ''}
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
                <div className="message-body">
                  <div className="message-heading">
                    <p className="message-author">
                      {message.role === 'assistant' ? 'OptiMind' : 'You'}
                    </p>
                    {message.role === 'assistant' && (
                      <button
                        aria-label="Copy reply"
                        className={`copy-message ${copiedMessageIndex === index ? 'copied' : ''}`}
                        disabled={!message.content || (isStreaming && index === messages.length - 1)}
                        onClick={() => void copyMessage(message.content, index)}
                        title="Copy reply"
                        type="button"
                      >
                        <span aria-hidden="true">{copiedMessageIndex === index ? '✓' : '▣'}</span>
                        {copiedMessageIndex === index ? 'Copied' : 'Copy'}
                      </button>
                    )}
                  </div>
                  <MessageImages images={message.images} />
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
              {attachedImages.length > 0 && (
                <div className="attachment-tray">
                  {attachedImages.map((image, index) => (
                    <div className="attachment-preview" key={`${image.name}-${index}`}>
                      <img
                        alt={image.name}
                        src={`data:${image.media_type};base64,${image.data}`}
                      />
                      <button
                        aria-label={`Remove ${image.name}`}
                        onClick={() => setAttachedImages((current) =>
                          current.filter((_, imageIndex) => imageIndex !== index)
                        )}
                        type="button"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <input
                accept="image/jpeg,image/png,image/webp"
                hidden
                multiple
                onChange={(event) => void attachImages(event.target.files)}
                ref={imageInputRef}
                type="file"
              />
              <button
                aria-label="Attach images"
                className="attach-button"
                disabled={isSending || attachedImages.length >= MAX_IMAGES}
                onClick={openImagePicker}
                title={supportsVision
                  ? 'Attach up to 3 images'
                  : 'Select a vision-capable model to attach images'}
                type="button"
              >
                ⌕
              </button>
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
                ref={composerRef}
                rows={1}
                value={draft}
              />
              {isSending ? (
                <button
                  className="stop-button"
                  onClick={stopGeneration}
                  type="button"
                >
                  <span>Stop</span> ■
                </button>
              ) : (
                <button disabled={!draft.trim() && attachedImages.length === 0} type="submit">
                  <span>Send</span> ↑
                </button>
              )}
            </form>
            <p className="composer-note">
              {attachedImages.length > 0
                ? `Image attached · ${selectedModel} is ready to process it`
                : webSearch
                  ? 'Web search on · Current sources will be cited'
                  : 'Local-first · Web search off'}
            </p>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App

