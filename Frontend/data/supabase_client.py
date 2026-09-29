"""Read-only Supabase client for the InfraWatch AI dashboard."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_FRONTEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _FRONTEND_DIR.parent

for _env_path in (_FRONTEND_DIR / ".env", _PROJECT_ROOT / ".env"):
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
        break
else:
    load_dotenv()


def get_supabase_config() -> tuple[str | None, str | None]:
    """Return (url, key) using the same env convention as ML Test."""
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    return url, key


@lru_cache(maxsize=1)
def get_supabase_client():
    """Create a single server-side Supabase client. Returns None if unconfigured."""
    url, key = get_supabase_config()
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)
