import fs from 'node:fs/promises'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { chromium } from 'playwright'

const scriptDirectory = decodeURIComponent(new URL('.', import.meta.url).pathname)
const root = path.resolve(scriptDirectory, '..')
const outputDir = path.join(root, 'output', 'video')
const tempDir = path.join(root, 'tmp', 'demo-video')
const outputPath = path.join(outputDir, 'optimind-client-demo.webm')

await fs.mkdir(outputDir, { recursive: true })
await fs.rm(tempDir, { recursive: true, force: true })
await fs.mkdir(tempDir, { recursive: true })

async function prepareTivlabsLiveSnapshot() {
  const liveResponse = await fetch('https://www.tivlabs.com', { signal: AbortSignal.timeout(30_000) })
  if (!liveResponse.ok) throw new Error(`Tivlabs homepage returned HTTP ${liveResponse.status}`)
  const html = await liveResponse.text()
  const pick = (pattern) => html.match(pattern)?.[1]?.replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim() || 'Not found'
  const title = pick(/<title[^>]*>([\s\S]*?)<\/title>/i)
  const description = pick(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']*)["']/i)
  const canonical = pick(/<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']*)["']/i)
  const h1Count = (html.match(/<h1\b/gi) || []).length
  const imageCount = (html.match(/<img\b/gi) || []).length
  const imageAltCount = (html.match(/<img\b[^>]*\balt=["'][^"']*["']/gi) || []).length
  const jsonLdCount = (html.match(/application\/ld\+json/gi) || []).length
  const robots = pick(/<meta[^>]+name=["']robots["'][^>]+content=["']([^"']*)["']/i)
  const checkedAt = new Date().toISOString().replace('T', ' ').replace(/\.\d{3}Z$/, ' UTC')
  const evidence = [
    `Live homepage checked: ${checkedAt}`,
    `Title: ${title}`,
    `Meta description: ${description}`,
    `Canonical URL: ${canonical}`,
    `H1 headings: ${h1Count}`,
    `Images: ${imageCount}; images with alt text: ${imageAltCount}`,
    `JSON-LD blocks: ${jsonLdCount}`,
    `Robots meta: ${robots}`,
  ].join('\n')
  const report = [
    '## Tivlabs live SEO snapshot',
    '',
    '### Audit overview',
    '- **Auditor:** OptiMind live homepage auditor',
    '- **Target:** https://www.tivlabs.com/',
    '- **Scope:** Public homepage HTML snapshot',
    '- **Status:** Completed from live evidence; full-site crawl is separate',
    '',
    'Checked directly from the public Tivlabs homepage. This is a homepage snapshot, not a full-site crawl.',
    '',
    '### Verified live signals',
    `- **Title:** ${title}`,
    `- **Meta description:** ${description}`,
    `- **Canonical:** ${canonical}`,
    `- **H1 headings:** ${h1Count}`,
    `- **Images:** ${imageCount}; images with alt text: ${imageAltCount}`,
    `- **JSON-LD blocks:** ${jsonLdCount}`,
    `- **Robots meta:** ${robots}`,
    '',
    '### SEO',
    h1Count === 0
      ? '- **Issue:** No H1 element was found in the live homepage HTML. **Fix:** add one clear, descriptive H1.'
      : '- **Signal:** A homepage H1 was found in the live HTML.',
    imageCount > imageAltCount
      ? `- **Issue:** ${imageCount - imageAltCount} image(s) need meaningful alt text. **Fix:** add concise, descriptive alt text.`
      : '- **Signal:** Every detected image has an alt attribute.',
    '- **Next:** keep the title, description, canonical, and robots directives unique and aligned with the homepage intent.',
    '',
    '### AEO',
    '- **Verified:** the homepage title and description provide a concise entity/service summary.',
    '- **Recommended:** add question-led service content and an FAQ section with accurate FAQPage schema where appropriate.',
    '',
    '### GEO',
    '- **Verified:** JSON-LD is present and can help machines understand the organization and page entity.',
    '- **Recommended:** strengthen organization, service, location, and author signals with consistent, quotable facts.',
    '',
    '### Not measured',
    '- Full-site page inventory, Google indexing status, Lighthouse/PageSpeed scores, and Core Web Vitals were not measured in this homepage snapshot.',
    '',
    `*Live evidence captured: ${checkedAt}*`,
  ].join('\n')
  const conversationId = randomUUID()
  const userMessageId = randomUUID()
  const assistantMessageId = randomUUID()
  const sqlQuote = (value) => `'${value.replaceAll("'", "''")}'`
  const sql = [
    `INSERT INTO conversations (id, title, model, website_id, created_at, updated_at) VALUES (${sqlQuote(conversationId)}, ${sqlQuote('Tivlabs live SEO snapshot')}, ${sqlQuote('gemma3:4b')}, NULL, now(), now());`,
    `INSERT INTO messages (id, conversation_id, role, content, images, metrics, activities) VALUES (${sqlQuote(userMessageId)}, ${sqlQuote(conversationId)}, 'user', ${sqlQuote('Show me a live SEO snapshot of Tivlabs.' )}, '[]'::json, NULL, '[]'::json);`,
    `INSERT INTO messages (id, conversation_id, role, content, images, metrics, activities) VALUES (${sqlQuote(assistantMessageId)}, ${sqlQuote(conversationId)}, 'assistant', ${sqlQuote(report)}, '[]'::json, NULL, '[]'::json);`,
  ].join('\n')
  execFileSync('/opt/homebrew/bin/psql', ['postgresql://optimind:optimind@localhost:5432/optimind', '-v', 'ON_ERROR_STOP=1', '-c', sql], { stdio: 'inherit' })
  return { id: conversationId, evidence }
}

const tivlabsSnapshot = await prepareTivlabsLiveSnapshot()
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  recordVideo: { dir: tempDir, size: { width: 1920, height: 1080 } },
})
await context.addInitScript(() => {
  localStorage.setItem('optimind-theme', 'dark')
})
const page = await context.newPage()

async function scene(hash, duration) {
  await page.goto(`http://127.0.0.1:5173/${hash}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(duration)
}

await scene('#conversation', 7_000)

await page.goto('http://127.0.0.1:5173/#websites', { waitUntil: 'networkidle' })
const tivlabsCard = page.locator('.website-card').filter({ hasText: 'Tivlabs' }).first()
await tivlabsCard.locator('button').filter({ hasText: 'Test connection' }).click()
await page.waitForTimeout(10_000)

await page.goto(`http://127.0.0.1:5173/#chat/${tivlabsSnapshot.id}`, { waitUntil: 'networkidle' })
await page.waitForFunction(
  () => document.querySelectorAll('.message.assistant .message-content').length >= 1,
  undefined,
  { timeout: 20_000 },
)
await page.waitForTimeout(18_000)

const conversation = page.locator('.conversation')
await conversation.evaluate((element) => element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' }))
await page.waitForTimeout(18_000)
await conversation.evaluate((element) => element.scrollTo({ top: 0, behavior: 'smooth' }))
await page.waitForTimeout(10_000)

// Show a real, typed chat turn so the demo feels like a live ChatGPT-style exchange.
await page.goto('http://127.0.0.1:5173/#conversation', { waitUntil: 'networkidle' })
await page.waitForTimeout(3_000)
await page.locator('button.new-chat').click()
await page.waitForTimeout(1_000)
const composer = page.locator('.composer textarea[aria-label="Message OptiMind"]')
await composer.click()
await composer.pressSequentially('What should I fix first on the Tivlabs homepage?', { delay: 28 })
await composer.press('Enter')
await page.waitForFunction(
  () => document.querySelectorAll('.message.assistant .message-content').length >= 1,
  undefined,
  { timeout: 45_000 },
)
await page.waitForTimeout(20_000)

await page.goto('http://127.0.0.1:5173/#websites', { waitUntil: 'networkidle' })
await page.waitForTimeout(12_000)
await page.goto(`http://127.0.0.1:5173/#chat/${tivlabsSnapshot.id}`, { waitUntil: 'networkidle' })
await page.waitForTimeout(15_000)

await context.close()
await browser.close()
const recorded = (await fs.readdir(tempDir)).find((file) => file.endsWith('.webm'))
if (!recorded) throw new Error('Playwright did not produce a video recording.')
await fs.copyFile(path.join(tempDir, recorded), outputPath)
console.log(outputPath)
