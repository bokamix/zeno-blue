# ZENO

Your personal AI agent. Runs locally as a native desktop app - no cloud, no Docker, no Redis.

## Install

**macOS / Linux**
```bash
curl -fsSL https://raw.githubusercontent.com/bokamix/zeno-blue/main/install.sh | bash
```

**Windows**
```powershell
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/bokamix/zeno-blue/main/install.ps1 | iex"
```

Then run:
```bash
zeno
```

## Development

```bash
git clone https://github.com/bokamix/zeno-blue.git
cd zeno-blue
make dev
```

This runs the app locally, identical to production. No `.env` needed — the setup screen in the browser will ask for your [OpenRouter](https://openrouter.ai) API key and access password on first run.

**Requirements:** Python 3.12+ (via [uv](https://docs.astral.sh/uv/)), Node.js (for frontend build).

### Other make targets

| Command | Description |
|---------|-------------|
| `make dev` | Run locally with auto-reload |
| `make frontend-dev` | Frontend dev server with hot reload |
| `make frontend-build` | Build frontend for production |
| `make logs id=<id>` | View logs for a conversation |

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

## License

MIT
