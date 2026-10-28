import fs from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(decodeURIComponent(new URL('.', import.meta.url).pathname), '..')
const outputDir = path.join(root, 'output', 'video')
const tempDir = path.join(root, 'tmp', 'landscape-chat-video')
const demoName = process.env.DEMO_NAME || 'optimind-image-landscape-chat-demo'
const outputPath = path.join(outputDir, `${demoName}.webm`)
const conversationId = process.env.CONVERSATION_ID
if (!conversationId) throw new Error('CONVERSATION_ID is required')
await fs.mkdir(outputDir, { recursive: true })
await fs.rm(tempDir, { recursive: true, force: true })
await fs.mkdir(tempDir, { recursive: true })
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, recordVideo: { dir: tempDir, size: { width: 1920, height: 1080 } } })
await context.addInitScript(() => localStorage.setItem('optimind-theme', 'dark'))
const page = await context.newPage()
await page.goto(`http://localhost:5173/#chat/${conversationId}`, { waitUntil: 'networkidle' })
await page.waitForFunction(() => document.querySelectorAll('.message-images img').length >= 1, undefined, { timeout: 20_000 })
await page.waitForTimeout(20_000)
await page.locator('.conversation').evaluate((element) => element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' }))
await page.waitForTimeout(15_000)
await context.close()
await browser.close()
const recorded = (await fs.readdir(tempDir)).find((file) => file.endsWith('.webm'))
if (!recorded) throw new Error('Playwright did not produce a video recording.')
await fs.copyFile(path.join(tempDir, recorded), outputPath)
console.log(outputPath)
