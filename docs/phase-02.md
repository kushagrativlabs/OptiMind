# Phase 2 — AI Chat and Agent System

## Goal

Turn the Phase 1 chat connection into an AI colleague that can manage persistent
sessions, use controlled tools, show its work, and let the user stop an active task.

## Progress

Phase 2 is **complete (5/5)**.

- [x] Build the Codex-style chat interface.
- [x] Create conversation sessions and persistent message history.
- [x] Implement the tool-calling architecture and tool registry.
- [x] Add task planning and visible execution logs.
- [x] Implement stop/cancel generation.

## Completed capabilities

- Streaming Ollama responses
- Selectable local models
- PostgreSQL conversation history
- Conversation deletion
- Markdown response rendering
- Web-search toggle and cited results
- URL scraping and bounded same-site crawling
- Stop button that cancels the active browser request and Ollama stream
- Typed, permission-aware registry for web search, webpage reading, and crawling
- Live task steps with planned, running, completed, and failed states
- Tool execution history stored with the assistant message

## Next implementation slice

Begin Phase 3 with stored website profiles, a website selector, public WordPress
connection testing, and website-specific conversation context. Credentials remain
out of scope until encrypted secret storage is configured.
