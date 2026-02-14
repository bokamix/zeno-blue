# Claude Code Instructions

## Project Overview

**ZENO** - autonomous AI agent, native desktop app. This repo contains:
- `user_container/` - Python backend with Agent, Tools, Skills
- `frontend/` - Vue 3 chat UI (Vite + Tailwind)
- Single-process architecture: FastAPI + asyncio, SQLite, no Redis/Docker required

**NEVER DELETE TODO.md!!!**

**Important distinction:**
- **ZENO** = the AI agent inside this codebase (in `user_container/agent/`)
- **You (Claude Code)** = helping develop ZENO, NOT being ZENO

## Running Commands

### Native (recommended for development)
```bash
# Start the server
python -m uvicorn user_container.app:app --host 127.0.0.1 --port 18000 --reload --reload-dir user_container

# Or use Docker (optional)
make up
```

### Docker (optional)
```bash
# Python one-liner (non-interactive, for AI agents)
make py CMD='from user_container.config import settings; print(settings.model_provider)'

# For complex code with quotes, use docker exec directly:
docker exec zeno python -c '
from user_container.tools.web_search import make_web_search_tool
print("works")
'

# Bash command in container
make sh CMD="ls -la /workspace"

# Interactive shell (for humans)
make bash
```

**Container name:** `zeno`
**Working directory in container:** `/app`

## Key Directories

```
user_container/
├── agent/           # Agent logic (agent.py, prompts.py, routing.py)
├── tools/           # Basic tools (shell, files, web_fetch, web_search)
├── skills/          # Dynamic skills (pdf, docx, etc.)
├── jobs/            # In-process job queue (queue.py) - replaces Redis
├── rag/             # RAG/memory system
├── db/              # SQLite database
└── config.py        # Settings from env vars

workspace/           # User workspace for artifacts
data/                # SQLite, ChromaDB data

frontend/            # Vue 3 frontend (built into frontend/dist/)
├── src/
│   ├── App.vue          # Main app component
│   ├── components/      # UI components (Sidebar, ChatMessage, etc.)
│   └── composables/     # Shared logic (useApi.js)
├── package.json
└── vite.config.js
```

## Architecture

Single-process, no external dependencies:
- **Job execution:** `asyncio.to_thread(agent.run)` - agent runs in thread, doesn't block FastAPI
- **Job queue:** In-memory (`asyncio.Queue`) + SQLite persistence (`user_container/jobs/queue.py`)
- **Ask-user flow:** `threading.Event` for sync/async bridge
- **Scheduler:** APScheduler in-process, enqueues directly to job queue
- **Database:** SQLite with WAL mode

## Frontend Development

**IMPORTANT: All frontend changes go to `frontend/src/`, NOT any root-level HTML files.**

### Frontend Requirements Checklist

All UI changes MUST work correctly on:
- **Desktop and mobile** - test responsive design, touch interactions
- **All supported languages** - currently EN and PL (`frontend/src/locales/`)
- **Dark and light mode** - use CSS variables like `var(--bg-surface)`, `var(--text-primary)` etc.

```bash
# Local development (hot reload)
make frontend-dev    # Runs Vite dev server on localhost:5173

# Build for production
make frontend-build  # Creates frontend/dist/

# Rebuild and restart Docker
make frontend-build && make up
```

**Key files:**
- `frontend/src/App.vue` - Main app logic, state management, API calls
- `frontend/src/components/Sidebar.vue` - File explorer + conversation list
- `frontend/src/components/LoadingIndicator.vue` - Activity log during agent work
- `frontend/src/composables/useApi.js` - API client wrapper

**URL routing:** App supports `/c/{conversation_id}` URLs. See `getConversationFromUrl()` in App.vue.

## Configuration

Key env vars in `.env`:
- `MODEL_PROVIDER` - "anthropic" or "openai"
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`
- `SERPER_API_KEY` - for web_search tool

## Testing

**User runs smoke tests manually.** Recommend running them when:
- After changes to `agent/agent.py`, `agent/routing.py`, `agent/delegate_executor.py`
- After adding/modifying tools in `tools/`
- After changes to `llm_client.py` or `prompts.py`
- Before committing significant changes

Just say: "Recommend running smoke tests now" - user will handle it.

## Git Commits

- Do NOT add "Co-Authored-By" lines to commit messages
- Keep commit messages concise and descriptive
