import fs from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(decodeURIComponent(new URL('.', import.meta.url).pathname), '..')
const outputDir = path.join(root, 'output', 'video')
const tempDir = path.join(root, 'tmp', 'basic-chat-video')
const outputPath = path.join(outputDir, 'optimind-basic-chat-demo.webm')

await fs.mkdir(outputDir, { recursive: true })
await fs.rm(tempDir, { recursive: true, force: true })
await fs.mkdir(tempDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  recordVideo: { dir: tempDir, size: { width: 1920, height: 1080 } },
})
await context.addInitScript(() => localStorage.setItem('optimind-theme', 'dark'))
const page = await context.newPage()

await page.goto('http://127.0.0.1:5173/#conversation', { waitUntil: 'networkidle' })
await page.waitForTimeout(5_000)
await page.locator('button.new-chat').click()
await page.waitForTimeout(2_000)

const composer = page.locator('.composer textarea[aria-label="Message OptiMind"]')
await composer.click()
await composer.pressSequentially('Work offline. How do I debounce a search input in JavaScript?', { delay: 35 })
await composer.press('Enter')
await page.waitForFunction(
  () => document.querySelectorAll('.message.assistant .message-content').length >= 1,
  undefined,
  { timeout: 45_000 },
)
await page.waitForTimeout(15_000)

await composer.click()
await composer.pressSequentially('Work offline. Suggest a relaxed Sunday morning routine.', { delay: 35 })
await composer.press('Enter')
await page.waitForFunction(
  () => document.querySelectorAll('.message.assistant .message-content').length >= 2,
  undefined,
  { timeout: 45_000 },
)
await page.waitForTimeout(20_000)

await context.close()
await browser.close()
const recorded = (await fs.readdir(tempDir)).find((file) => file.endsWith('.webm'))
if (!recorded) throw new Error('Playwright did not produce a video recording.')
await fs.copyFile(path.join(tempDir, recorded), outputPath)
console.log(outputPath)
