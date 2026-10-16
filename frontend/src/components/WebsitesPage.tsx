import { FormEvent, useState } from 'react'

import {
  createWebsite,
  deleteWebsite,
  OllamaModel,
  testWebsite,
  updateWebsite,
  Website,
  WebsiteConnectionResult,
} from '../services/api'

type WebsitesPageProps = {
  models: OllamaModel[]
  websites: Website[]
  defaultModel: string
  error: string | null
  onChange: (websites: Website[]) => void
  onError: (message: string | null) => void
  onOpen: (website: Website) => void
}

export const WebsitesPage = ({
  models,
  websites,
  defaultModel,
  error,
  onChange,
  onError,
  onOpen,
}: WebsitesPageProps) => {
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [model, setModel] = useState(defaultModel)
  const [isCreating, setIsCreating] = useState(false)
  const [busyWebsiteId, setBusyWebsiteId] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, WebsiteConnectionResult>>({})

  const addWebsite = async (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim() || !url.trim() || isCreating) return
    setIsCreating(true)
    onError(null)
    try {
      const website = await createWebsite({
        name: name.trim(),
        url: url.trim(),
        model: model || defaultModel,
      })
      onChange([...websites, website].sort((left, right) => left.name.localeCompare(right.name)))
      setName('')
      setUrl('')
    } catch (requestError) {
      onError(requestError instanceof Error ? requestError.message : 'Could not add website.')
    } finally {
      setIsCreating(false)
    }
  }

  const changeModel = async (website: Website, nextModel: string) => {
    setBusyWebsiteId(website.id)
    onError(null)
    try {
      const updated = await updateWebsite(website.id, { model: nextModel })
      onChange(websites.map((item) => item.id === updated.id ? updated : item))
    } catch (requestError) {
      onError(requestError instanceof Error ? requestError.message : 'Could not update model.')
    } finally {
      setBusyWebsiteId(null)
    }
  }

  const checkConnection = async (website: Website) => {
    setBusyWebsiteId(website.id)
    onError(null)
    try {
      const result = await testWebsite(website.id)
      setResults((current) => ({ ...current, [website.id]: result }))
    } catch (requestError) {
      onError(requestError instanceof Error ? requestError.message : 'Connection test failed.')
    } finally {
      setBusyWebsiteId(null)
    }
  }

  const removeWebsite = async (website: Website) => {
    if (!window.confirm(`Remove “${website.name}”? Its conversations will be kept.`)) return
    setBusyWebsiteId(website.id)
    onError(null)
    try {
      await deleteWebsite(website.id)
      onChange(websites.filter((item) => item.id !== website.id))
    } catch (requestError) {
      onError(requestError instanceof Error ? requestError.message : 'Could not remove website.')
    } finally {
      setBusyWebsiteId(null)
    }
  }

  return (
    <div className="websites-page">
      <header className="websites-header">
        <div>
          <p className="eyebrow">PHASE 3 · WEBSITE WORKSPACES</p>
          <h1>Websites</h1>
          <p>Add each WordPress project and give it a preferred local model.</p>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="website-create-card">
        <div>
          <h2>Add a website</h2>
          <p>OptiMind stores the public URLs now. Credentials are added later with encryption.</p>
        </div>
        <form onSubmit={addWebsite}>
          <label>
            <span>Website name</span>
            <input
              onChange={(event) => setName(event.target.value)}
              placeholder="My company website"
              value={name}
            />
          </label>
          <label>
            <span>Website URL</span>
            <input
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://example.com"
              type="url"
              value={url}
            />
          </label>
          <label>
            <span>Preferred model</span>
            <select onChange={(event) => setModel(event.target.value)} value={model}>
              {models.length === 0 ? (
                <option value={model}>{model}</option>
              ) : models.map((item) => (
                <option key={item.name} value={item.name}>{item.name}</option>
              ))}
            </select>
          </label>
          <button disabled={isCreating || !name.trim() || !url.trim()} type="submit">
            {isCreating ? 'Adding…' : 'Add website'}
          </button>
        </form>
      </section>

      <section className="website-list" aria-label="Saved websites">
        <div className="website-list-heading">
          <h2>Your websites</h2>
          <span>{websites.length}</span>
        </div>
        {websites.length === 0 ? (
          <div className="website-empty">
            <span aria-hidden="true">◇</span>
            <h3>No websites added yet</h3>
            <p>Add your first site above to create a dedicated AI workspace.</p>
          </div>
        ) : (
          <div className="website-grid">
            {websites.map((website) => {
              const result = results[website.id]
              const busy = busyWebsiteId === website.id
              return (
                <article className="website-card" key={website.id}>
                  <div className="website-card-title">
                    <div className="website-icon">◇</div>
                    <div>
                      <h3>{website.name}</h3>
                      <a href={website.url} rel="noreferrer" target="_blank">{website.url}</a>
                    </div>
                  </div>
                  <label>
                    <span>Website model</span>
                    <select
                      disabled={busy}
                      onChange={(event) => void changeModel(website, event.target.value)}
                      value={website.model}
                    >
                      {models.map((item) => (
                        <option key={item.name} value={item.name}>{item.name}</option>
                      ))}
                    </select>
                  </label>
                  {result && (
                    <div className={`website-test-result ${result.wordpress_detected ? 'success' : 'warning'}`}>
                      <strong>{result.wordpress_detected ? 'WordPress connected' : 'Check needed'}</strong>
                      <span>{result.detail}</span>
                    </div>
                  )}
                  <div className="website-card-actions">
                    <button className="primary" disabled={busy} onClick={() => onOpen(website)}>
                      Open workspace
                    </button>
                    <button disabled={busy} onClick={() => void checkConnection(website)}>
                      {busy ? 'Checking…' : 'Test connection'}
                    </button>
                    <button className="danger" disabled={busy} onClick={() => void removeWebsite(website)}>
                      Remove
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
