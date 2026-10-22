import { Children, FormEvent, isValidElement, ReactNode, useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { WebsitesPage } from './components/WebsitesPage'
import {
  AgentActivity,
  ChatMessage,
  ChatImage,
  ConversationSummary,
  deleteConversation,
  generateImage,
  getConversation,
  getConversations,
  getModels,
  getSystemStatus,
  getWebsites,
  OllamaModel,
  streamChat,
  ServiceState,
  SystemStatus,
  Website,
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
      {images.map((image, index) => {
        const source = `data:${image.media_type};base64,${image.data}`
        return (
          <figure key={`${image.name}-${index}`}>
            <img alt={image.name} src={source} />
            <a download={image.name} href={source}>Download image</a>
          </figure>
        )
      })}
    </div>
  )
}

const nodeText = (node: ReactNode): string => {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(nodeText).join('')
  if (isValidElement<{ children?: ReactNode }>(node)) return nodeText(node.props.children)
  return ''
}

const CodeBlock = ({ children }: { children?: ReactNode }) => {
  const [copied, setCopied] = useState(false)
  const codeElement = Children.toArray(children)[0]
  const language = isValidElement<{ className?: string }>(codeElement)
    ? codeElement.props.className?.replace('language-', '')
    : undefined
  const code = nodeText(codeElement).replace(/\n$/, '')

  const copyCode = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div className="code-block">
      <div className="code-block-heading">
        <span>{language || 'Code'}</span>
        <button onClick={() => void copyCode()} type="button">
          <span aria-hidden="true">{copied ? '✓' : '▣'}</span>
          {copied ? 'Copied' : 'Copy code'}
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  )
}

const normalizeMarkdown = (content: string) => {
  const escapedMarkdown = (content.match(/\\(?:[*_`#>~-])/g) ?? []).length
  if (escapedMarkdown < 2) return content
  return content
    .replace(/\\([*_`#>~-])/g, '$1')
    .replace(/\\\((.*?)\\\)/g, '($1)')
    // Some local models emit `+ item` as a list marker. Normalize it to
    // Markdown's standard bullet marker before rendering or copying.
    .replace(/^\s*\+\s+(?=\S)/gm, '- ')
}

const routeFromHash = () => {
  const hash = window.location.hash
  if (hash === '#websites') {
    return { view: 'websites' as const, conversationId: null }
  }
  if (hash === '#audits') {
    return { view: 'audits' as const, conversationId: null }
  }

  const match = hash.match(/^#chat\/([^/]+)$/)
  return {
    view: 'conversation' as const,
    conversationId: match?.[1] ?? null,
  }
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
          pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
        }}
        remarkPlugins={[remarkGfm]}
      >
        {normalizeMarkdown(content)}
      </ReactMarkdown>
    </div>
  )
}

const AuditsPage = ({
  audits,
  websites,
  onOpen,
}: {
  audits: ConversationSummary[]
  websites: Website[]
  onOpen: (id: string) => void
}) => (
  <section className="audits-page">
    <header className="audits-header">
      <div>
        <p className="eyebrow">REPORT LIBRARY</p>
        <h1>Website audits</h1>
        <p>Saved SEO, AEO, GEO, indexability, and Lighthouse reports.</p>
      </div>
      <div className="audit-count">{audits.length} report{audits.length === 1 ? '' : 's'}</div>
    </header>
    {audits.length === 0 ? (
      <div className="audit-empty">
        <span>⌁</span>
        <h2>No audits yet</h2>
        <p>Open a website workspace and run a full audit to create your first report.</p>
      </div>
    ) : (
      <div className="audit-grid">
        {audits.map((audit) => {
          const website = websites.find((item) => item.id === audit.website_id)
          return (
            <article className="audit-card" key={audit.id}>
              <div className="audit-card-top">
                <span className="audit-icon">⌁</span>
                <span className="audit-status">Saved report</span>
              </div>
              <h2>{audit.title}</h2>
              <p className="audit-website">{website?.name ?? 'Website workspace'}</p>
              <div className="audit-meta">
                <span>{new Date(audit.updated_at).toLocaleDateString()}</span>
                <span>{audit.model}</span>
              </div>
              <button className="primary" onClick={() => onOpen(audit.id)} type="button">
                Open report <span aria-hidden="true">→</span>
              </button>
            </article>
          )
        })}
      </div>
    )}
  </section>
)

const formatDuration = (seconds: number) => {
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ${Math.round(seconds % 60)}s`
}

const downloadConversationPdf = (
  messages: ChatMessage[],
  websiteName?: string,
  model?: string,
) => {
  const safeText = (value: string) => value
    .normalize('NFKD')
    .replace(/[^\x20-\x7E\n]/g, '?')
  const wrap = (value: string, width = 92) => {
    const words = safeText(value).split(/\s+/)
    const lines: string[] = []
    let line = ''
    for (const word of words) {
      if (!word) continue
      if (line && `${line} ${word}`.length > width) {
        lines.push(line)
        line = word
      } else {
        line = line ? `${line} ${word}` : word
      }
    }
    if (line) lines.push(line)
    return lines.length ? lines : ['']
  }
  const pdfText = (value: string) => normalizeMarkdown(value)
    .replace(/⭐{4}/g, 'Critical')
    .replace(/⭐{3}/g, 'High')
    .replace(/⭐{2}/g, 'Medium')
    .replace(/⭐/g, 'Low')
    .replace(/```[^\n]*\n?/g, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1 ($2)')
    .replace(/(\*\*|__)(.*?)\1/g, '$2')
    .replace(/(^|\s)[*_]([^*_]+)[*_](?=\s|$)/gm, '$1$2')
    .replace(/[*_]+/g, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/^\s*#{1,6}\s+/gm, '')
    .replace(/^\?+\s*/gm, '')

  type ReportLine = {
    text: string
    kind: 'title' | 'meta' | 'heading' | 'label' | 'body' | 'tableHeader' | 'tableRow'
    cells?: string[]
  }
  const tableCells = (line: string) => line
    .trim()
    .replace(/^\||\|$/g, '')
    .split('|')
    .map((cell) => pdfText(cell.trim()))
  const messageLines = (message: ChatMessage): ReportLine[] => {
    const lines = message.content.split('\n')
    const result: ReportLine[] = [
      { text: `${message.role === 'assistant' ? 'OptiMind' : 'You'}:`, kind: 'label' },
    ]
    let tableStarted = false
    const sectionHeadings = /^(Full Report|SEO Report|AEO Report|GEO Report|Page-by-Page Audit|Verified findings:?|Impact:|Prioritized recommendations:?|Exact changes to make:?|Verified checks|Verified issues|Recommended fixes)$/i
  const pageField = /^[-*+•]?\s*(Title|Meta description|Meta Description|Canonical|Robots|Headings|Schema|Images|Key content|Content summary):\s*(.*)$/i
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index]
      const isTableLine = /^\s*\|.*\|\s*$/.test(line)
      const isSeparator = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(line)
      if (isTableLine && !isSeparator) {
        const cells = tableCells(line)
        result.push({ text: '', cells, kind: tableStarted ? 'tableRow' : 'tableHeader' })
        tableStarted = true
        continue
      }
      if (isSeparator && tableStarted) continue
      tableStarted = false
      const heading = line.match(/^#{1,3}\s+(.+)/)?.[1]
      const cleanedHeading = heading ? pdfText(heading).replace(/^[^A-Za-z0-9]+/, '') : null
      const plainLine = pdfText(line).trim()
      const pageMatch = plainLine.match(/^Page:\s*(.+)$/i)
      if (pageMatch) {
        result.push({ text: `Page: ${pageMatch[1]}`, kind: 'heading' })
        const rows: string[][] = []
        while (index + 1 < lines.length) {
          const next = pdfText(lines[index + 1]).trim()
          const field = next.match(pageField)
          if (!field) break
          rows.push([field[1], field[2] || 'Not found'])
          index += 1
        }
        if (rows.length) {
          result.push({ text: '', cells: ['Verified field', 'Value'], kind: 'tableHeader' })
          rows.forEach((cells) => result.push({ text: '', cells, kind: 'tableRow' }))
        }
        continue
      }
      const inferredHeading = Boolean(heading) || sectionHeadings.test(plainLine)
      result.push(...wrap(cleanedHeading ?? plainLine).map((text) => ({
        text,
        kind: inferredHeading ? 'heading' as const : 'body' as const,
      })))
      if (index < lines.length - 1 && line.trim() === '') result.push({ text: '', kind: 'body' })
    }
    result.push({ text: '', kind: 'body' })
    return result
  }
  const auditMessages = messages.filter((message) => message.role === 'assistant').slice(-1)
  const reportDate = new Date().toLocaleString()
  const contentLines: ReportLine[] = [
    { text: 'OptiMind Website Audit Report', kind: 'title' },
    { text: websiteName ? `Website: ${websiteName}` : 'Website workspace report', kind: 'meta' },
    { text: 'SEO · AEO · GEO review', kind: 'meta' },
    { text: model ? `Model: ${model}` : 'Model: local AI', kind: 'meta' },
    { text: `Generated: ${reportDate}`, kind: 'meta' },
    { text: 'This report contains verified observations from the website crawl followed by recommended actions.', kind: 'body' },
    { text: '', kind: 'body' },
    ...auditMessages.flatMap(messageLines),
  ]
  // Build pages from the actual rendered height instead of a fixed line count.
  // This keeps tables and wrapped paragraphs from running into the footer.
  const pageLines: ReportLine[][] = []
  let currentPage: ReportLine[] = []
  let remaining = 650
  contentLines.forEach((line) => {
    const height = line.cells
      ? (line.kind === 'tableHeader' ? 30 : 42)
      : line.kind === 'title' ? 38 : line.kind === 'heading' ? 24 : line.kind === 'meta' ? 17 : 16
    if (currentPage.length && remaining < height) {
      pageLines.push(currentPage)
      currentPage = []
      remaining = 650
    }
    currentPage.push(line)
    remaining -= height
  })
  if (currentPage.length) pageLines.push(currentPage)
  const objects: string[] = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>',
  ]
  const pageObjectIds: number[] = []
  const contentObjectIds: number[] = []
  pageLines.forEach((lines, pageIndex) => {
    pageObjectIds.push(objects.length + 1)
    objects.push('')
    contentObjectIds.push(objects.length + 1)
    let currentY = pageIndex === 0 ? 708 : 744
    const textCommands = lines.map((line) => {
      if (line.cells) {
        const columnWidth = 516 / line.cells.length
        const rowHeight = line.kind === 'tableHeader' ? 30 : 42
        const top = currentY + 4
        const fill = line.kind === 'tableHeader' ? '0.80 0.91 0.85 rg' : '0.96 0.98 0.97 rg'
        const cells = line.cells.map((cell, cellIndex) => {
          const x = 48 + cellIndex * columnWidth
          const text = wrap(cell, 24).slice(0, 2)
          const cellText = text.map((value, textIndex) =>
            `0.12 0.16 0.15 rg BT /F${line.kind === 'tableHeader' ? '2' : '1'} 8 Tf ${x + 6} ${top - 13 - textIndex * 9} Td (${value.replace(/[\\()]/g, '\\$&')}) Tj ET`,
          ).join('\n')
          return `${fill}\n${x} ${top - rowHeight} ${columnWidth} ${rowHeight} re f\n0.78 0.84 0.80 RG 0.5 w ${x} ${top - rowHeight} ${columnWidth} ${rowHeight} re S\n${cellText}`
        }).join('\n')
        currentY -= rowHeight + 5
        return cells
      }
      const font = line.kind === 'title' || line.kind === 'heading' || line.kind === 'label' ? 'F2' : 'F1'
      const size = line.kind === 'title' ? 22 : line.kind === 'heading' ? 13 : line.kind === 'meta' ? 9 : 10
      const color = line.kind === 'title' ? '0.10 0.30 0.23 rg' : line.kind === 'heading' ? '0.18 0.42 0.34 rg' : '0.12 0.16 0.15 rg'
      const command = `${color}\nBT\n/${font} ${size} Tf\n48 ${currentY} Td\n(${line.text.replace(/[\\()]/g, '\\$&')}) Tj\nET`
      currentY -= line.kind === 'title' ? 32 : line.kind === 'heading' ? 22 : line.kind === 'meta' ? 15 : 14
      return command
    }).join('\n')
    const stream = [
      'q',
      '0.12 0.34 0.27 rg',
      '0 770 612 22 re f',
      pageIndex === 0 ? '0.86 0.94 0.89 rg 36 674 540 58 re f' : '',
      'Q',
      textCommands,
      '0.45 0.50 0.47 rg BT /F1 8 Tf 48 28 Td',
      `(OptiMind  |  Website audit  |  Page ${pageIndex + 1} of ${pageLines.length}) Tj ET`,
    ].join('\n')
    objects.push(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`)
  })
  objects[1] = `<< /Type /Pages /Kids [${pageObjectIds.map((id) => `${id} 0 R`).join(' ')}] /Count ${pageObjectIds.length} >>`
  pageObjectIds.forEach((id, index) => {
    objects[id - 1] = `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${contentObjectIds[index]} 0 R >>`
  })
  let pdf = '%PDF-1.4\n'
  const offsets = [0]
  objects.forEach((object, index) => {
    offsets.push(pdf.length)
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`
  })
  const xrefOffset = pdf.length
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  pdf += offsets.slice(1).map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`
  const url = URL.createObjectURL(new Blob([pdf], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `${(websiteName || 'optimind-website-audit').replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.pdf`
  link.click()
  URL.revokeObjectURL(url)
}

const MessageMetrics = ({ metrics }: { metrics?: ChatMessage['metrics'] }) => {
  if (!metrics) return null
  return (
    <div className="message-metrics" aria-label="Generation performance">
      {metrics.tokens_per_second != null && (
        <span>{metrics.tokens_per_second.toFixed(1)} tok/s</span>
      )}
      <span>{formatDuration(metrics.duration_seconds)}</span>
    </div>
  )
}

const ActivityLog = ({
  activities = [],
  live = false,
}: {
  activities?: AgentActivity[]
  live?: boolean
}) => {
  if (activities.length === 0) return null
  const complete = activities.every((activity) => activity.status === 'completed')
  return (
    <details className="activity-log" open={live || !complete}>
      <summary>
        <span aria-hidden="true">{complete ? '✓' : '⌁'}</span>
        {live ? 'Working plan' : `Work completed · ${activities.length} step${activities.length === 1 ? '' : 's'}`}
      </summary>
      <ol>
        {activities.map((activity) => (
          <li className={activity.status} key={activity.id}>
            <span className="activity-state" aria-hidden="true">
              {activity.status === 'completed'
                ? '✓'
                : activity.status === 'failed'
                  ? '!'
                  : activity.status === 'running'
                    ? '●'
                    : '○'}
            </span>
            <span>
              <strong>{activity.label}</strong>
              {activity.detail && <small>{activity.detail}</small>}
            </span>
          </li>
        ))}
      </ol>
    </details>
  )
}

function App() {
  const initialRoute = routeFromHash()
  const [view, setView] = useState<'conversation' | 'websites' | 'audits'>(initialRoute.view)
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
  const [websites, setWebsites] = useState<Website[]>([])
  const [activeWebsiteId, setActiveWebsiteId] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [routeConversationId, setRouteConversationId] = useState<string | null>(
    initialRoute.conversationId,
  )
  const [draft, setDraft] = useState('')
  const [attachedImages, setAttachedImages] = useState<ChatImage[]>([])
  const [isSending, setIsSending] = useState(false)
  const [deletingConversationId, setDeletingConversationId] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [activeActivities, setActiveActivities] = useState<AgentActivity[]>([])
  const [error, setError] = useState<string | null>(null)
  const [copiedMessageIndex, setCopiedMessageIndex] = useState<number | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const composerFormRef = useRef<HTMLFormElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const activeRequestRef = useRef<AbortController | null>(null)
  const activeActivitiesRef = useRef<AgentActivity[]>([])
  const selectedModelInfo = models.find((model) => model.name === selectedModel)
  const supportsVision = selectedModelInfo?.capabilities.includes('vision') ?? false
  const activeWebsite = websites.find((website) => website.id === activeWebsiteId) ?? null
  const visibleConversations = activeWebsiteId
    ? conversations.filter((conversation) => conversation.website_id === activeWebsiteId)
    : conversations
  const audits = conversations.filter((conversation) => conversation.website_id !== null)

  const refreshStatus = async () => {
    try {
      setStatus(await getSystemStatus())
    } catch {
      setStatus(null)
    }
  }

  const refreshConnections = async () => {
    const [statusResult, modelsResult] = await Promise.allSettled([
      getSystemStatus(),
      getModels(),
    ])

    if (statusResult.status === 'fulfilled') {
      setStatus(statusResult.value)
      setSelectedModel((current) => {
        const availableModels = modelsResult.status === 'fulfilled' ? modelsResult.value : []
        if (availableModels.some((model) => model.name === current)) return current
        const configured = availableModels.find(
          (model) => model.name === statusResult.value.ollama.model,
        )
        return configured?.name ?? availableModels[0]?.name ?? current
      })
    } else {
      setStatus(null)
    }

    if (modelsResult.status === 'fulfilled') {
      setModels(modelsResult.value)
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
    void refreshConnections()
  }, [])

  useEffect(() => {
    let active = true
    getWebsites()
      .then((savedWebsites) => {
        if (active) setWebsites(savedWebsites)
      })
      .catch(() => {
        if (active) setWebsites([])
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const updateRoute = () => {
      const route = routeFromHash()
      setView(route.view)
      setRouteConversationId(route.conversationId)
    }
    window.addEventListener('hashchange', updateRoute)
    window.addEventListener('popstate', updateRoute)
    return () => {
      window.removeEventListener('hashchange', updateRoute)
      window.removeEventListener('popstate', updateRoute)
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
    setActiveActivities([])
    activeActivitiesRef.current = []
    requestAnimationFrame(() => composerRef.current?.focus())
  }

  const openConversation = useCallback(async (id: string) => {
    if (isSending) return
    setError(null)

    try {
      const conversation = await getConversation(id)
      setConversationId(conversation.id)
      setSelectedModel(conversation.model)
      setActiveWebsiteId(conversation.website_id)
      setMessages([initialMessage, ...conversation.messages])
      setView('conversation')
      setRouteConversationId(conversation.id)
      window.history.pushState(null, '', `#chat/${conversation.id}`)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Could not load that conversation.',
      )
    }
  }, [isSending])

  useEffect(() => {
    if (!routeConversationId || routeConversationId === conversationId || isSending) return
    const timer = window.setTimeout(() => {
      void openConversation(routeConversationId)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [routeConversationId, conversationId, isSending, openConversation])

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
    const hasAttachedImages = attachedImages.length > 0
    const imageGenerationIntent = /\b(?:generate|create|draw|make|design|render)\b[\s\S]*\b(?:image|picture|illustration|logo|poster|icon)\b/i.test(content)
    const shouldGenerateImage = !hasAttachedImages && imageGenerationIntent
    const webSearchIntent = /\b(?:latest|current|news|search|google|competitor|trend|research|source|citation)\b/i.test(content)
    const shouldSearchWeb = status?.web_search.status === 'online' && webSearchIntent
    const visionModel = models.find((model) => model.capabilities.includes('vision'))
    const requestModel = hasAttachedImages && !supportsVision
      ? visionModel?.name ?? selectedModel
      : selectedModel

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
    setActiveActivities([])
    activeActivitiesRef.current = []
    const controller = new AbortController()
    activeRequestRef.current = controller

    try {
      if (shouldGenerateImage) {
        const result = await generateImage(
          content,
          requestModel,
          conversationId,
          activeWebsiteId,
          controller.signal,
        )
        setConversationId(result.conversation_id)
        setMessages((current) => [...current, result.message])
        await refreshConversations()
        return
      }
      await streamChat(
        nextMessages.slice(1),
        requestModel,
        conversationId,
        shouldSearchWeb,
        activeWebsiteId,
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
              return [
                ...current,
                {
                  role: 'assistant',
                  content: chunk,
                  activities: activeActivitiesRef.current,
                },
              ]
            })
          },
          onActivity: (activity) => {
            const existingIndex = activeActivitiesRef.current.findIndex(
              (item) => item.id === activity.id,
            )
            const nextActivities = existingIndex === -1
              ? [...activeActivitiesRef.current, activity]
              : activeActivitiesRef.current.map((item) =>
                  item.id === activity.id ? activity : item
                )
            activeActivitiesRef.current = nextActivities
            setActiveActivities(nextActivities)
            setMessages((current) => {
              const lastMessage = current.at(-1)
              if (lastMessage?.role !== 'assistant') return current
              return [
                ...current.slice(0, -1),
                { ...lastMessage, activities: nextActivities },
              ]
            })
          },
          onMetrics: (metrics) => {
            setMessages((current) => {
              const lastMessage = current.at(-1)
              if (lastMessage?.role !== 'assistant') return current
              return [
                ...current.slice(0, -1),
                { ...lastMessage, metrics },
              ]
            })
          },
        },
        controller.signal,
      )
      await refreshConversations()
    } catch (requestError) {
      // Leaving the page, switching conversations, or pressing Stop intentionally
      // aborts the request. Browser fetch can report this as AbortError or TypeError.
      if (
        controller.signal.aborted ||
        (requestError instanceof Error && requestError.name === 'AbortError')
      ) {
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
      setActiveActivities([])
      activeActivitiesRef.current = []
    }
  }

  const stopGeneration = () => {
    const controller = activeRequestRef.current
    if (!controller) return
    controller.abort()
    setIsSending(false)
    setIsStreaming(false)
    setActiveActivities([])
    activeActivitiesRef.current = []
  }

  const showGlobalConversation = () => {
    setActiveWebsiteId(null)
    startConversation()
    setView('conversation')
    setRouteConversationId(null)
    window.history.pushState(null, '', '#conversation')
  }

  const openWebsiteWorkspace = (website: Website) => {
    setActiveWebsiteId(website.id)
    setSelectedModel(website.model)
    startConversation()
    setDraft(
      `Review ${website.url}. Summarize its main pages, verify its content and SEO/AEO/GEO issues, ` +
      'then provide a full report with dedicated sections for SEO, AEO (answer-engine visibility), ' +
      'and GEO (generative-engine visibility). For each section include verified findings, impact, ' +
      'and prioritized recommendations with the exact changes to make. Include a dedicated ' +
      'page-by-page audit for every crawled URL. Use a heading `Page: <full URL>` for every page, ' +
      'followed by separate Checks, Issues, and Recommended fixes subsections. Include the page ' +
      'title, meta description, canonical, robots, headings, schema, image/alt-text status, and ' +
      'key content in its page section.',
    )
    setView('conversation')
    setRouteConversationId(null)
    window.history.pushState(null, '', '#conversation')
    requestAnimationFrame(() => composerFormRef.current?.requestSubmit())
  }

  const copyMessage = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(normalizeMarkdown(content))
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

        <button
          className="new-chat"
          onClick={() => {
            startConversation()
            setActiveWebsiteId(null)
            setView('conversation')
            setRouteConversationId(null)
            window.history.pushState(null, '', '#conversation')
          }}
        >
          <span>＋</span> New conversation
        </button>

        <nav aria-label="Workspace">
          <p className="nav-label">Workspace</p>
          <a
            className={`nav-item ${view === 'conversation' ? 'active' : ''}`}
            href="#conversation"
            onClick={(event) => {
              event.preventDefault()
              showGlobalConversation()
            }}
          >
            <span>◌</span> Conversation
          </a>
          <a
            className={`nav-item ${view === 'websites' ? 'active' : ''}`}
            href="#websites"
            onClick={(event) => {
              event.preventDefault()
              setError(null)
              setView('websites')
              window.history.pushState(null, '', '#websites')
            }}
          >
            <span>◇</span> Websites <small>{websites.length}</small>
          </a>
          <a
            className={`nav-item ${view === 'audits' ? 'active' : ''}`}
            href="#audits"
            onClick={(event) => {
              event.preventDefault()
              setError(null)
              setView('audits')
              window.history.pushState(null, '', '#audits')
            }}
          >
            <span>⌁</span> Audits <small>{audits.length}</small>
          </a>
        </nav>

        <section className="history" aria-label="Conversation history">
          <p className="nav-label">History</p>
          {visibleConversations.length === 0 ? (
            <p className="history-empty">No saved conversations yet</p>
          ) : (
            <div className="history-list">
              {visibleConversations.map((conversation) => (
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
          <StatusPill label="Image Generator" service={status?.image_generation} />
          <StatusPill label="Web Search" service={status?.web_search} />
          <button className="refresh-button" onClick={() => void refreshConnections()}>
            Refresh connections
          </button>
        </div>
      </aside>

      <main className="main" id={view}>
        {view === 'websites' ? (
          <WebsitesPage
            defaultModel={selectedModel}
            error={error}
            models={models}
            onChange={setWebsites}
            onError={setError}
            onOpen={openWebsiteWorkspace}
            websites={websites}
          />
        ) : view === 'audits' ? (
          <AuditsPage audits={audits} onOpen={(id) => void openConversation(id)} websites={websites} />
        ) : (
        <>
        <header className="topbar">
          <div>
            <p className="eyebrow">PRIVATE WORKSPACE</p>
            <h1>Website growth assistant</h1>
            {activeWebsite && (
              <button
                className="active-website"
                onClick={() => {
                  setView('websites')
                  window.history.pushState(null, '', '#websites')
                }}
                type="button"
              >
                <span>◇</span> {activeWebsite.name}
              </button>
            )}
          </div>
          <div className="topbar-actions">
            <button
              className="theme-toggle"
              disabled={messages.length < 2 || isSending}
              onClick={() => downloadConversationPdf(messages, activeWebsite?.name, selectedModel)}
              title="Download the SEO, AEO, and GEO audit as a PDF"
              type="button"
            >
              <span aria-hidden="true">⇩</span>
              <strong>PDF</strong>
            </button>
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
                        aria-label="Copy reply as Markdown"
                        className={`copy-message ${copiedMessageIndex === index ? 'copied' : ''}`}
                        disabled={!message.content || (isStreaming && index === messages.length - 1)}
                        onClick={() => void copyMessage(message.content, index)}
                        title="Copy the complete reply as Markdown"
                        type="button"
                      >
                        <span aria-hidden="true">{copiedMessageIndex === index ? '✓' : '▣'}</span>
                        {copiedMessageIndex === index ? 'Copied' : 'Copy Markdown'}
                      </button>
                    )}
                  </div>
                  <ActivityLog activities={message.activities} />
                  <MessageImages images={message.images} />
                  <MessageText content={message.content} />
                  {message.role === 'assistant' && <MessageMetrics metrics={message.metrics} />}
                </div>
              </article>
            ))}
            {isSending && !isStreaming && (
              <article className="message assistant">
                <div className="avatar">O</div>
                <div>
                  <p className="message-author">OptiMind</p>
                  <ActivityLog activities={activeActivities} live />
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
            <form className="composer" onSubmit={submit} ref={composerFormRef}>
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
                placeholder="Ask OptiMind anything…"
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
                ? `Image attached · OptiMind will review it automatically`
                : 'OptiMind automatically chooses chat, web search, image review, or image generation'}
            </p>
          </div>
        </section>
        </>
        )}
      </main>
    </div>
  )
}

export default App

