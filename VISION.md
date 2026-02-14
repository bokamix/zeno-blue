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
One ZENO instance = one user. Simple, no auth complexity. Lightweight enough to run on a Raspberry Pi or a $5/mo VPS.

### Always-on (24/7 service)
- **Scheduler** - Cron-like task scheduling ("every Monday at 9am, generate sales report")
- **Triggers/Webhooks** - React to external events (incoming email, API call, file change)
- **Background tasks** - Long-running jobs that don't block the UI
- **Monitoring** - Watch for conditions and act automatically

### AI Model Flexibility
Users connect whatever models they want:
- **Cloud APIs** - Anthropic, OpenAI, Google (API key)
- **Local models** - Ollama, LM Studio (privacy, free, offline)
- **Custom endpoints** - OpenRouter, Azure, self-hosted (any OpenAI-compatible API)

### Extensibility System (Skills & Tools)

**Built-in tools** - Shell, files, web search, web fetch, document processing

**Skill Marketplace** - Community-driven repository where users:
- Browse and install skills with one click
- Rate and review skills
- See what's popular / trending

**Custom skills** - Users write their own in Python:
- Simple API: define inputs, outputs, and logic
- Drop a file into `skills/` directory
- Automatically discovered and available to the agent

### Full Internet Access
- Web search (configurable search providers)
- Fetch and parse web pages
- Call external APIs
- Receive incoming webhooks
- Send notifications (email, Slack, Discord, etc.)

## Installation

Single bash script - no Docker required:
```bash
curl -fsSL https://get.zeno.ai | bash
```

The script handles:
1. Check system requirements (Python, Node.js)
2. Download and set up ZENO
3. Launch setup wizard in browser
4. User enters API key (or configures local model)
5. Done - ZENO is running

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
| 24/7 autonomous | Yes | No | Yes | Partial |
| Simple setup | Yes | Yes | Medium | Hard |
| Skill marketplace | Yes | No | Yes | No |
| Local model support | Yes | Yes | No | No |
| Non-technical users | Yes | Yes | No | No |

## Roadmap (High-level)

### Phase 1 - Foundation (Current)
- [x] Core agent with tool use
- [x] Chat UI (Vue 3)
- [x] Basic tools (shell, files, web)
- [x] Multi-model support (Anthropic, OpenAI)
- [ ] Local model support (Ollama)
- [ ] Stable skill/plugin API

### Phase 2 - Autonomy
- [ ] Scheduler (cron-like tasks)
- [ ] Webhook triggers
- [ ] Background task management UI
- [ ] Notification system (email, Slack, Discord)
- [ ] File watcher triggers

### Phase 3 - Ecosystem
- [ ] Skill marketplace (browse, install, rate)
- [ ] Community skill repository
- [ ] Skill creation wizard in UI
- [ ] Skill templates and docs

### Phase 4 - Polish & Growth
- [ ] One-line installer script
- [ ] Setup wizard (web-based)
- [ ] Mobile-friendly UI
- [ ] Internationalization
- [ ] Cloud deploy templates (DigitalOcean, Railway, etc.)

---

*This is a living document. Updated as the vision evolves.*
