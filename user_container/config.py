from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel
import os

class Settings(BaseModel):
    # Build info
    build_version: str = os.getenv("BUILD_VERSION", "dev")
    build_time: str = os.getenv("BUILD_TIME", "unknown")
    git_hash: str = os.getenv("GIT_HASH", "unknown")

    # Paths - defaults for native mode (zeno.py overrides these via env vars)
    workspace_dir: str = os.getenv("WORKSPACE_DIR", os.path.join(os.path.expanduser("~"), ".zeno", "workspace"))
    artifacts_dir: str = os.getenv("ARTIFACTS_DIR", os.path.join(os.path.expanduser("~"), ".zeno", "workspace", "artifacts"))
    skills_dir: str = os.getenv("SKILLS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills"))
    data_dir: str = os.getenv("DATA_DIR", os.path.join(os.path.expanduser("~"), ".zeno", "data"))
    db_path: str = os.getenv("DB_PATH", os.path.join(os.path.expanduser("~"), ".zeno", "data", "runtime.db"))

    # Port pool for spawned user apps
    app_port_min: int = int(os.getenv("APP_PORT_MIN", "3100"))
    app_port_max: int = int(os.getenv("APP_PORT_MAX", "3199"))

    # LLM Configuration (via OpenRouter)
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5-20250929")
    openrouter_cheap_model: str = os.getenv("OPENROUTER_CHEAP_MODEL", "anthropic/claude-haiku-4-5-20251001")

    # Groq Configuration (fast routing)
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    groq_routing_model: str = os.getenv("GROQ_ROUTING_MODEL", "llama-3.1-8b-instant")
    routing_provider: str = os.getenv("ROUTING_PROVIDER", "auto")  # "auto", "groq", "default"

    # Agent settings
    agent_max_tool_calls: int = int(os.getenv("AGENT_MAX_TOOL_CALLS", "50"))
    agent_max_steps: int = int(os.getenv("AGENT_MAX_STEPS", "100"))
    subtask_max_steps: int = int(os.getenv("SUBTASK_MAX_STEPS", "50"))  # Max steps per subtask in orchestrated execution
    skill_ttl: int = int(os.getenv("SKILL_TTL", "5"))  # How many steps a skill stays active
    reflection_interval: int = int(os.getenv("REFLECTION_INTERVAL", "7"))  # Reflect every N steps (0 = disabled)
    conversation_max_delegates: int = int(os.getenv("CONVERSATION_MAX_DELEGATES", "25"))  # Max delegate_task calls per conversation

    # Context compression settings
    context_max_tokens: int = int(os.getenv("CONTEXT_MAX_TOKENS", "200000"))  # Model's context limit (Claude Sonnet/Haiku support 200k)
    context_compression_threshold: float = float(os.getenv("CONTEXT_COMPRESSION_THRESHOLD", "0.7"))  # Compress at 70%
    context_keep_recent: int = int(os.getenv("CONTEXT_KEEP_RECENT", "5"))  # Keep last N messages

    # Conversation Summary settings (hierarchical memory)
    summary_threshold: int = int(os.getenv("SUMMARY_THRESHOLD", "15"))  # Start summarizing after N messages
    summary_update_interval: int = int(os.getenv("SUMMARY_UPDATE_INTERVAL", "10"))  # Update summary every N new messages
    summary_max_tokens: int = int(os.getenv("SUMMARY_MAX_TOKENS", "1000"))  # Max summary length in tokens

    # Recent Messages (intelligent compression)
    # Old approach (token budgets) removed - caused orphan tool_results
    # New approach: compress old messages, keep recent exchanges full
    recent_exchanges_full: int = int(os.getenv("RECENT_EXCHANGES_FULL", "5"))  # Keep last N user-assistant exchanges full

    # Job settings
    max_job_runtime: int = int(os.getenv("MAX_JOB_RUNTIME", "1800"))  # Max job runtime in seconds (default 30 min)

    # External APIs
    serper_api_key: Optional[str] = os.getenv("SERPER_API_KEY")

    # Base URL
    base_url: str = os.getenv("BASE_URL", "http://localhost:18000")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Langfuse (optional observability)
    langfuse_public_key: Optional[str] = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: Optional[str] = os.getenv("LANGFUSE_SECRET_KEY")
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    langfuse_tags: Optional[str] = os.getenv("LANGFUSE_TAGS")  # Comma-separated tags, e.g. "experiment:v2,env:prod"

    # Auth (opt-in password protection for remote access)
    auth_password: Optional[str] = os.getenv("ZENO_PASSWORD")  # None = no auth (localhost mode)
    auth_session_ttl: int = int(os.getenv("AUTH_SESSION_TTL", "604800"))  # 7 days

    # Admin panel (HTTP Basic Auth)
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: Optional[str] = os.getenv("ADMIN_PASSWORD")  # None = admin panel disabled

    # Sentry Error Tracking
    sentry_dsn: Optional[str] = os.getenv("SENTRY_DSN")  # None = Sentry disabled
    sentry_environment: str = os.getenv("SENTRY_ENVIRONMENT", "development")
    sentry_traces_sample_rate: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

    @property
    def debug(self) -> bool:
        return self.log_level == "DEBUG"

settings = Settings()


def get_app_url(app_id: str) -> str:
    """
    Generate app URL based on BASE_URL.

    Local (localhost/has port): http://{app_id}.lvh.me:{port}/
    Production ({user_id}.{domain}): {scheme}://{app_id}.{user_id}.{domain}/
    """
    parsed = urlparse(settings.base_url)
    scheme = parsed.scheme  # http or https
    host = parsed.hostname  # e.g., "localhost" or "user-001.zeno.blue"
    port = parsed.port      # e.g., 18000 or None

    # Local mode: localhost or has explicit port
    if host in ("localhost", "127.0.0.1") or port:
        port_suffix = f":{port}" if port else ":18000"
        return f"http://{app_id}.lvh.me{port_suffix}/"

    # Production mode: {app_id}.{base_host} (subdomain of subdomain)
    # e.g., user-001.zeno.blue → my-app.user-001.zeno.blue
    return f"{scheme}://{app_id}.{host}/"
