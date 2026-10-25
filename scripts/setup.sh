#!/usr/bin/env bash
# First-run setup for The ZeroHour Times. Safe to re-run: it never overwrites
# an existing .env, profile.md or config.json without asking.
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf '\n\033[1m%s\033[0m\n' "$1"; }
ask() { local p="$1" d="${2:-}" a; read -rp "$p${d:+ [$d]}: " a; printf '%s' "${a:-$d}"; }

say "The ZeroHour Times — setup"
echo "This writes three files: .env (secrets), config.json (what to watch),"
echo "and profile.md (who you are). All three are gitignored."

# ---- .env -------------------------------------------------------------------
if [ -f .env ]; then
  echo; read -rp ".env already exists. Leave it alone? [Y/n]: " keep
  [[ "${keep:-Y}" =~ ^[Nn] ]] && rm -f .env
fi
if [ ! -f .env ]; then
  cp .env.example .env
  gen() { python3 -c "import secrets;print(secrets.token_urlsafe(32))"; }
  say "Generating JobSync secrets"
  python3 - "$(gen)" "$(gen)" <<'PY'
import sys, pathlib
auth, enc = sys.argv[1], sys.argv[2]
p = pathlib.Path(".env"); s = p.read_text()
s = s.replace("AUTH_SECRET=\n", f"AUTH_SECRET={auth}\n")
s = s.replace("ENCRYPTION_KEY=\n", f"ENCRYPTION_KEY={enc}\n")
p.write_text(s)
PY
  echo "  written to .env."
  echo "  ** Copy ENCRYPTION_KEY somewhere safe now. If you lose it, the AI provider"
  echo "     keys JobSync stores cannot be recovered. **"

  tz="$(ask 'Your timezone (IANA, e.g. America/Denver)' "${TZ:-UTC}")"
  runat="$(ask 'What local time should the daily run start?' '07:10')"
  key="$(ask 'OpenAI API key (press enter to skip — you can add it later)' '')"
  python3 - "$tz" "$runat" "$key" <<'PY'
import sys, pathlib
tz, runat, key = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(".env"); s = p.read_text()
s = s.replace("ZHT_TZ=UTC", f"ZHT_TZ={tz}")
s = s.replace("ZHT_RUN_AT=07:10", f"ZHT_RUN_AT={runat}")
if key:
    s = s.replace("OPENAI_API_KEY=\n", f"OPENAI_API_KEY={key}\n")
p.write_text(s)
PY
fi

# ---- config.json -------------------------------------------------------------
if [ ! -f config.json ]; then
  cp config.example.json config.json
  say "config.json created from the example"
  echo "  It ships with 5 example employer job boards — enough to see the shape."
  echo "  Want a bigger net? starter-watchlist.json holds 119 verified boards to"
  echo "  copy entries from. To add companies by name instead, put one per line in"
  echo "  a file and run:"
  echo "    python3 zhtimes/resolve.py --names employers.txt --merge config.json"
  echo "  Edit filters.titleAny / titleNone to match the roles you actually want."
fi

# ---- profile.md ---------------------------------------------------------------
if [ ! -f profile.md ]; then
  say "Your profile"
  echo "The AI assesses jobs against this file, and is instructed never to claim"
  echo "anything that is not in it. Start from the template and edit it — honestly."
  cp profile.example.md profile.md
  echo "  profile.md created. Open it and replace the placeholders before your first run."
fi

say "Next steps"
cat <<'NEXT'
  1. docker compose up -d
  2. Open JobSync at http://localhost:3737 and CREATE YOUR ACCOUNT IMMEDIATELY —
     signup is open by default, so the first person to reach it gets the account.
  3. In JobSync: Settings -> MCP -> create a token, scope it to jobs:write only,
     set an expiry. Put it in .env as JOBSYNC_MCP_TOKEN.
  4. docker compose restart zerohour-times
  5. Open your newspaper at http://localhost:8099

  Want to look around first? `docker compose -f docker-compose.demo.yml up --build`
  builds the dashboard from bundled sample data — no keys, no JobSync needed.
NEXT
