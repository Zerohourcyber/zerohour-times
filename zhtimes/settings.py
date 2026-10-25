#!/usr/bin/env python3
"""Every environment-specific value in one place, driven by env vars.

Defaults assume the bundled Docker Compose setup, so `docker compose up` works
with no configuration at all. Each one can be overridden in `.env`.

Secrets are read from a file when a *_FILE variable is set and otherwise from
the environment, so you can use Docker secrets, a mounted file, or plain env —
whichever your setup prefers. Nothing is ever written back here.
"""

import os


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def secret(name, default=None):
    """Read a secret from <NAME>_FILE if set, else <NAME>, else default.

    The file form is preferred: it keeps the value out of `docker inspect`,
    out of the process environment, and out of any crash dump that prints env.
    """
    path = _env(f"{name}_FILE")
    if path:
        try:
            with open(path) as fh:
                return fh.read().strip()
        except OSError:
            return default
    return _env(name, default)


# --- where things live -------------------------------------------------------
# Writable state: the queue, assessment log, research log, spend ledger, the
# generated dashboard. One directory so a single volume mount covers all of it.
STATE_DIR = _env("ZHT_STATE_DIR", "/data")
WWW_DIR = _env("ZHT_WWW_DIR", f"{STATE_DIR}/www")

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = _env("ZHT_CONFIG", os.path.join(APP_DIR, "config.json"))
PROFILE_PATH = _env("ZHT_PROFILE", os.path.join(APP_DIR, "profile.md"))
PROMPT_PATH = _env("ZHT_PROMPT", os.path.join(APP_DIR, "prompts", "match-v6.md"))

# --- JobSync -----------------------------------------------------------------
# Defaults to the compose service name. Point this at an existing JobSync with
# JOBSYNC_URL=http://host:3737 if you already run one.
JOBSYNC_URL = _env("JOBSYNC_URL", "http://jobsync:3737").rstrip("/")
MCP_URL = f"{JOBSYNC_URL}/api/mcp"
# Minted in the JobSync UI: Settings -> MCP. Scope it to jobs:write only.
MCP_TOKEN = secret("JOBSYNC_MCP_TOKEN")

# --- AI provider -------------------------------------------------------------
OPENAI_API_KEY = secret("OPENAI_API_KEY")
OPENAI_BASE = _env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_CHAT = f"{OPENAI_BASE}/chat/completions"
OPENAI_RESPONSES = f"{OPENAI_BASE}/responses"

# --- behaviour ---------------------------------------------------------------
# Used for scheduling and for every date shown to a human. Any IANA zone.
TZ_NAME = _env("ZHT_TZ", _env("TZ", "UTC"))
# JobSync allows 100 MCP calls per hour per token. Discovery runs before
# matching and they share that ceiling, so discovery is capped below half to
# leave the stage behind it room to work.
MCP_CALL_BUDGET = int(_env("ZHT_MCP_CALL_BUDGET", "45"))
DAILY_RUN_AT = _env("ZHT_RUN_AT", "07:10")       # local time, HH:MM

USER_AGENT = _env("ZHT_USER_AGENT",
                  "zerohour-times/1.0 (personal job search; +https://github.com/)")

# --- dashboard ---------------------------------------------------------------
# 127.0.0.1 by default. The dashboard is READ-ONLY AND UNAUTHENTICATED: anyone
# who can reach the port can read your assessments and your profile-derived
# analysis. Only widen this to a private interface you control.
DASHBOARD_BIND = _env("ZHT_DASHBOARD_BIND", "127.0.0.1")
DASHBOARD_PORT = int(_env("ZHT_DASHBOARD_PORT", "8099"))
