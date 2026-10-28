import fs from 'node:fs'
import { execFileSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'

const imagePath = '/Users/kushagramaurya/.codex/generated_images/01a13901-edc5-7ee3-81bf-1e208870259d/exec-4009dc36-e9da-47bc-9552-852382d664d2.png'
const image = fs.readFileSync(imagePath).toString('base64')
const conversationId = randomUUID()
const userId = randomUUID()
const assistantId = randomUUID()
const prompt = 'Create a photorealistic real-world image of a glassy mountain lake at sunrise, pine forest reflections, soft golden light, cinematic photography.'
const content = 'Generated image demo — photorealistic mountain lake at sunrise.'
const images = JSON.stringify([{ name: 'mountain-lake.png', media_type: 'image/png', data: image }])
const quote = (value) => `'${value.replaceAll("'", "''")}'`
const sql = [
  `INSERT INTO conversations (id, title, model, website_id, created_at, updated_at) VALUES (${quote(conversationId)}, ${quote('Image: Mountain lake sunrise')}, ${quote('lcm-ssd-1b-q4')}, NULL, now(), now());`,
  `INSERT INTO messages (id, conversation_id, role, content, images, metrics, activities) VALUES (${quote(userId)}, ${quote(conversationId)}, 'user', ${quote(prompt)}, '[]'::json, NULL, '[]'::json);`,
  `INSERT INTO messages (id, conversation_id, role, content, images, metrics, activities) VALUES (${quote(assistantId)}, ${quote(conversationId)}, 'assistant', ${quote(content)}, ${quote(images)}::json, NULL, '[]'::json);`,
].join('\n')
execFileSync('/opt/homebrew/bin/psql', ['postgresql://optimind:optimind@localhost:5432/optimind', '-v', 'ON_ERROR_STOP=1'], { input: sql, stdio: ['pipe', 'inherit', 'inherit'] })
console.log(conversationId)
