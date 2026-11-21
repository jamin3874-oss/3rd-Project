"""Backend-only config. Never expose credentials in API responses or GitHub."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_backend_env(path=None):
    """Load .env for local development, preserving existing environment variables."""
    env_file = Path(path) if path is not None else ROOT / '.env'
    if not env_file.is_file():
        return
    for raw in env_file.read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if key not in ('ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_MODEL'):
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
