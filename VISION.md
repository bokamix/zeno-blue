# ZENO - Vision

## One-liner

**Self-hosted autonomous AI agent that runs 24/7 on your server, uses your models, and automates your life.**

## What is ZENO?

ZENO is an open-source, self-hosted AI agent. Not a chatbot - a true autonomous agent that plans, executes, monitors, and reacts on its own. Users deploy it on their own hardware, connect their own AI models (cloud or local), and let it handle automations around the clock.

**Your agent. Your data. Your models. Zero cloud dependency.**

## Core Principles

1. **Privacy-first** - Everything runs on user's machine. No data leaves unless the user explicitly configures it. Local models supported for full offline operation.
2. **True autonomy** - Not just a chat interface. ZENO runs 24/7, executes scheduled tasks, reacts to triggers, monitors and acts without user intervention.
3. **Dead simple** - One bash script to install. Clean UI that non-technical users can navigate. No Docker knowledge required, no complex configuration.
4. **Extensible from day one** - Plugin/skill marketplace + ability to write custom tools. Community-driven ecosystem of automations.
5. **Full open-source** - No paid tiers, no premium features. User pays only for their own API keys (or runs free local models).

## Target User

**Broad audience** - not just developers. Anyone who wants a personal AI agent:
- Small business owner automating reports and emails
- Freelancer managing tasks and scraping data
- Student organizing research and notes
- Developer automating workflows
- Anyone who wants AI that works for them 24/7

Setup should be achievable by anyone who can follow a simple guide (copy-paste a bash command, enter API key in UI).

## Primary Use Cases

### Business & Data Automation
- Generate reports from data sources on schedule
- Web scraping and data collection
- Email automation and monitoring
- API integrations (CRM, analytics, etc.)
- Document processing (PDF, DOCX, spreadsheets)

### Personal Assistant
- File management and organization
- Note-taking and knowledge management
- Task management with smart scheduling
- Calendar integrations
- Web research and summarization

## Architecture Pillars

### Single-user, single-process
One ZENO instance = one user. Simple, no auth complexity. Lightweight enough to run on a Raspberry Pi or a $5/mo VPS. FastAPI + asyncio, SQLite with WAL mode, no Redis/Docker required.

### Always-on (24/7 service)
- **CRON Scheduler** - APScheduler-based task scheduling ("every Monday at 9am, generate sales report")
- **Background jobs** - In-memory queue + SQLite persistence, long-running jobs don't block the UI
- **Triggers/Webhooks** - React to external events (planned: incoming HTTP, file changes)

### Intelligent Routing & Delegation
- **Routing agent** - Classifies task complexity (depth 0 = direct answer, 1 = standard, 2 = complex)
- **Delegation** - Parallel sub-agents using cheap models (Haiku) for independent subtasks
- **Exploration** - Dedicated executor for codebase analysis and research

### AI Model Flexibility
Users connect whatever models they want:
- **Cloud APIs** - Anthropic (Claude Sonnet/Haiku/Opus), OpenAI (GPT-5/5-mini)
- **Fast routing** - Groq (Llama 3.1) for instant task classification
- **Planned** - Ollama, LM Studio, OpenRouter, Azure, any OpenAI-compatible endpoint

### Extensibility System (Skills & Tools)

**16 built-in tools** - Shell, file ops (read/write/edit/list), web search, web fetch, search in files, delegate, explore, schedule, ask user, recall from chat

**12 skills** with intelligent routing (TTL-based decay):
- **Documents** - PDF (extract, create, merge, split, fill forms), DOCX, XLSX
- **Media** - Image analysis (Claude/GPT-4V vision), audio/video transcription (Whisper)
- **Web** - Screenshots (Playwright), web app builder (FastAPI + Alpine.js + Tailwind)
- **Deployment** - App deploy & manage (register, start, stop, restart, logs, port management)
- **Design** - Frontend design, n8n workflow generation

**Custom skills** - Users write their own in Python:
- Simple API: define inputs, outputs, and logic
- Drop a file into `skills/` directory
- Automatically discovered via SKILL.md format

### Apps System
Users can deploy custom web apps directly from ZENO:
- FastAPI-based apps with automatic port assignment (3100-3199)
- Full lifecycle management (register, start, stop, restart, delete, update, logs)
- SQLite-tracked app state with PID management

### Context & Cost Management
- **Context compression** - Automatic compression at 70% of context window, preserves recent messages and decisions
- **Conversation summarization** - Hierarchical memory with semantic summaries
- **Cost tracking** - Per-request token usage and cost calculation, integrated with Langfuse observability
- **Skill usage tracking** - Monitor API consumption per skill

### Full Internet Access
- Web search (Serper API)
- Fetch and parse web pages
- Call external APIs
- Planned: incoming webhooks, notifications (email, Slack, Discord)

## Installation

One command to install, one command to run:
```bash
# Install
curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash

# Run
zeno
```

The `install.sh` script handles:
1. OS detection (macOS/Linux, suggests WSL for Windows)
2. Install `uv` (Python package manager)
3. Download and extract ZENO to `~/.zeno/`
4. Create virtual environment and install dependencies
5. Create `zeno` CLI wrapper
6. Launch setup wizard in browser - user enters API key and configures preferences

## What ZENO is NOT

- **Not a chatbot wrapper** - It's an autonomous agent, not just a UI for GPT
- **Not a SaaS** - No accounts, no subscriptions, no vendor lock-in
- **Not enterprise software** - Single-user, simple, personal
- **Not a no-code platform** - It has a chat interface, not a drag-and-drop workflow builder (though skills can be installed without code)

## Competitive Landscape

| Feature | ZENO | Open WebUI | n8n | AutoGPT |
|---------|------|-----------|-----|---------|
| Self-hosted | Yes | Yes | Yes | Yes |
| True agent (not just chat) | Yes | No | Partial | Yes |
| 24/7 scheduled tasks | Yes | No | Yes | No |
| Simple one-command setup | Yes | Yes | Medium | Hard |
| Skill/plugin system | Yes (12 built-in) | Partial | Yes | No |
| App deployment | Yes | No | No | No |
| Task delegation | Yes (parallel) | No | Yes (workflows) | Partial |
| Multi-model (cloud) | Yes (3 providers) | Yes | No | Partial |
| Cost tracking | Yes | No | No | No |
| Non-technical users | Yes | Yes | No | No |
| Responsive UI + i18n | Yes (EN, PL) | Yes | Partial | No |

## Roadmap

### Phase 1 - Foundation (DONE)
- [x] Core agent with intelligent routing (depth 0-2) and delegation
- [x] Chat UI (Vue 3, responsive, dark/light mode, i18n EN+PL)
- [x] 16 tools (shell, files, web, delegate, explore, schedule, ask_user, recall...)
- [x] 12 skills (PDF, DOCX, XLSX, image, transcription, web-app-builder, app-deploy...)
- [x] Skill router with TTL-based decay
- [x] Multi-model support (Anthropic, OpenAI, Groq for routing)
- [x] CRON scheduler with APScheduler + background job queue
- [x] Apps system (deploy and manage user web apps)
- [x] Setup wizard + bash installer (`install.sh` → `zeno` CLI)
- [x] Cost tracking + usage monitoring (Langfuse integration)
- [x] Context compression + conversation summarization
- [x] File management with drag-and-drop upload

### Phase 2 - Ecosystem (NEXT)
- [ ] Skill marketplace (community repo, browse, install, rate)
- [ ] Skill creation wizard in UI
- [ ] Skill templates and documentation for contributors

### Phase 3 - Event-driven Automation (NEXT)
- [ ] Webhook triggers (react to incoming HTTP events)
- [ ] File watcher triggers
- [ ] Notification system (email, Slack, Discord, webhooks out)
- [ ] Event chaining (trigger A fires task B)

### Phase 4 - Model Flexibility
- [ ] Ollama / LM Studio support (local models)
- [ ] Custom OpenAI-compatible endpoints (OpenRouter, Azure, self-hosted)
- [ ] Model routing rules (use local for simple, cloud for complex)

### Phase 5 - Growth
- [ ] Cloud deploy templates (DigitalOcean, Railway, Render)
- [ ] RAG / semantic search (vector DB for knowledge base)
- [ ] More languages (i18n expansion)
- [ ] Plugin API for custom tools (not just skills)

---

*This is a living document. Updated as the vision evolves.*



Niech da się exportować ustawienia projektu (pliki synchronizowane przez s3 lub firebase)


zeno.blue trzymsa klucze bazy itd