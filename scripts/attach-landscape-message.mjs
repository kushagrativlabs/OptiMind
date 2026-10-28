import fs from 'node:fs'
import { execFileSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'

const conversationId = process.env.CONVERSATION_ID
if (!conversationId) throw new Error('CONVERSATION_ID is required')
const image = fs.readFileSync('/tmp/optimind-landscape-768.png').toString('base64')
const messageId = randomUUID()
const quote = (value) => `'${value.replaceAll("'", "''")}'`
const images = JSON.stringify([{ name: 'mountain-lake.png', media_type: 'image/png', data: image }])
const sql = `INSERT INTO messages (id, conversation_id, role, content, images, metrics, activities) VALUES (${quote(messageId)}, ${quote(conversationId)}, 'assistant', ${quote('Generated image demo — photorealistic mountain lake at sunrise.')}, ${quote(images)}::json, NULL, '[]'::json);`
execFileSync('/opt/homebrew/bin/psql', ['postgresql://optimind:optimind@localhost:5432/optimind', '-v', 'ON_ERROR_STOP=1'], { input: sql, stdio: ['pipe', 'inherit', 'inherit'] })
console.log('attached', messageId)
