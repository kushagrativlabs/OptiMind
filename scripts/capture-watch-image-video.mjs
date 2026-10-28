import fs from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright'

const root = path.resolve(decodeURIComponent(new URL('.', import.meta.url).pathname), '..')
const outputDir = path.join(root, 'output', 'video')
const tempDir = path.join(root, 'tmp', 'watch-image-video')
const outputPath = path.join(outputDir, 'optimind-watch-image-prompt-demo.webm')
const prompt = 'Generate an image: Luxury advertising photograph of a black titanium mechanical wristwatch floating above a polished obsidian surface. Intricate visible gears, sapphire crystal, brushed metal, realistic reflections, tiny water droplets, dramatic rim lighting, deep black background, premium Swiss watch advertising aesthetic, macro photography, 8K detail.'

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
await page.goto('http://localhost:5173/#conversation', { waitUntil: 'networkidle' })
await page.waitForTimeout(2_000)
await page.locator('button.new-chat').click()
await page.waitForTimeout(1_500)
const composer = page.locator('.composer textarea[aria-label="Message OptiMind"]')
await composer.click()
await composer.pressSequentially(prompt, { delay: 12 })
await page.waitForTimeout(2_000)
await composer.press('Enter')
await page.waitForFunction(() => document.querySelectorAll('.message-images img').length >= 1, undefined, { timeout: 180_000 })
await page.waitForTimeout(12_000)
await page.locator('.conversation').evaluate((element) => element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' }))
await page.waitForTimeout(4_000)
await context.close()
await browser.close()

const recorded = (await fs.readdir(tempDir)).find((file) => file.endsWith('.webm'))
if (!recorded) throw new Error('Playwright did not produce a video recording.')
await fs.copyFile(path.join(tempDir, recorded), outputPath)
console.log(outputPath)
