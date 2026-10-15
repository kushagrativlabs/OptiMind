# Phase 2 — AI Chat and Agent System

## Goal

Turn the Phase 1 chat connection into an AI colleague that can manage persistent
sessions, use controlled tools, show its work, and let the user stop an active task.

## Progress

Phase 2 is currently **3/5 complete**.

- [x] Build the Codex-style chat interface.
- [x] Create conversation sessions and persistent message history.
- [ ] Implement the tool-calling architecture and tool registry.
- [ ] Add task planning and visible execution logs.
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

## Next implementation slice

Create a backend tool registry with typed inputs, explicit permission metadata,
execution results, and stream events. The first registered tools will be read-only:
web search, webpage retrieval, and website crawling. Task planning and execution
logs will then consume the same event format.
