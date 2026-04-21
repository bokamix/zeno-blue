# ZENO

Your personal AI agent. Runs locally as a native desktop app - no cloud, no Docker, no Redis.

## Install

**macOS / Linux / VPS**
```bash
curl -fsSL https://raw.githubusercontent.com/bokamix/zeno-blue/main/server-install.sh | bash
```

Automatically detects the environment:
- **macOS / WSL** — installs and opens in browser at `localhost`
- **Linux VPS (systemd)** — installs, sets up HTTPS via Caddy, prints your URL

**Windows**
```powershell
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/bokamix/zeno-blue/main/install.ps1 | iex"
```

Then run:
```powershell
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

## Security Notice

> **This application is currently in early development and has not undergone a security audit.**
>
> ZENO is intended to be run in **isolated or disposable environments only** — such as a dedicated virtual machine or a Docker container. Do not run it on devices where a security compromise would be unacceptable (e.g. your primary work machine, production servers, or systems storing sensitive data). The following limitations apply:
>
> - Authentication is based on a single shared access password — no user account system or session management is implemented.
> - The application has **not been hardened** against malicious input or unauthorized access.
> - No penetration testing or formal security review has been performed.
>
> **Run this application only on machines you can afford to compromise.** Use at your own risk.
>
> Security improvements are planned for future releases.

## License

MIT
