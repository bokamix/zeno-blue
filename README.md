# ZENO

Your personal AI agent. Runs locally as a native desktop app - no cloud, no Docker, no Redis.

## Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp env.example .env
   # Edit .env and set your API key (ANTHROPIC_API_KEY or OPENAI_API_KEY)
   ```

3. **Create data directories**
   ```bash
   mkdir -p workspace data
   ```

4. **Run**
   ```bash
   python -m uvicorn user_container.app:app --host 127.0.0.1 --port 18000
   ```

5. Open http://localhost:18000 in your browser.

## Configuration

Key env vars in `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `MODEL_PROVIDER` | LLM provider | `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-proj-...` |
| `SERPER_API_KEY` | Web search API key (optional) | `...` |

## Architecture

Single-process, zero external dependencies:

```
Python process
  └─ FastAPI + uvicorn
      └─ Agent runs in asyncio.to_thread()
      └─ SQLite (data + job state)
      └─ In-process job queue (no Redis)
      └─ APScheduler (in-process)
```

## Docker (optional)

You can also run with Docker:

```bash
make up
```

## Frontend Development

```bash
# Install deps
cd frontend && npm install

# Dev server with hot reload
make frontend-dev

# Build for production
make frontend-build
```

## License

MIT
