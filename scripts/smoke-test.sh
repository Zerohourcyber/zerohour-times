#!/usr/bin/env bash
# End-to-end smoke test: discovery -> assessment -> validation -> research -> newspaper.
#
# THIS SPENDS REAL MONEY. It makes a small number of AI calls against your own
# API key. It refuses to run without --i-will-pay, and it caps itself hard:
# at most 3 assessments and 1 research call, under a $0.25 ceiling it writes
# into the config for the duration of the run and restores afterwards.
#
# Expected cost: roughly $0.11 (3 x ~$0.02 assessment + 1 x ~$0.05 research).
#
#   ./scripts/smoke-test.sh              # dry run: checks prerequisites, spends nothing
#   ./scripts/smoke-test.sh --i-will-pay # the real thing
set -uo pipefail
cd "$(dirname "$0")/.."

PAY=0; [ "${1:-}" = "--i-will-pay" ] && PAY=1
COMPOSE="docker compose"
SVC=zerohour-times
pass=0; fail=0
ok(){ printf '  \033[32mPASS\033[0m  %s\n' "$1"; pass=$((pass+1)); }
no(){ printf '  \033[31mFAIL\033[0m  %s\n' "$1"; fail=$((fail+1)); }
inf(){ printf '        %s\n' "$1"; }

say(){ printf '\n\033[1m%s\033[0m\n' "$1"; }
exec_in(){ $COMPOSE exec -T "$SVC" "$@" 2>/dev/null; }

say "0. Prerequisites"
PS="$($COMPOSE ps --format '{{.Service}} {{.Status}}' 2>/dev/null || true)"
printf '%s' "$PS" | grep -q "jobsync.*healthy" \
  && ok "JobSync is up and healthy" || no "JobSync is not healthy — docker compose up -d"
printf '%s' "$PS" | grep -q "$SVC.*healthy" \
  && ok "The ZeroHour Times is up" || no "app container is not healthy"
exec_in python3 -c "import sys;sys.path.insert(0,'/app/zhtimes');import settings as S;sys.exit(0 if S.MCP_TOKEN else 1)" 2>/dev/null \
  && ok "JOBSYNC_MCP_TOKEN is set" || no "JOBSYNC_MCP_TOKEN missing — see docs/CONNECT-JOBSYNC.md"
exec_in python3 -c "import sys;sys.path.insert(0,'/app/zhtimes');import settings as S;sys.exit(0 if S.OPENAI_API_KEY else 1)" 2>/dev/null \
  && ok "OPENAI_API_KEY is set" || no "OPENAI_API_KEY missing — add it to .env"
exec_in test -s /app/profile.md && ok "profile.md is present" || no "profile.md missing or empty"

if [ "$fail" -gt 0 ]; then
  printf '\n\033[31mPrerequisites failed — fix the above before running the paid test.\033[0m\n'
  exit 1
fi

if [ "$PAY" -ne 1 ]; then
  cat <<'DRY'

Dry run complete. Prerequisites look good.

This test would, with your API key:
  1. discover  — poll your watchlist boards            (free)
  2. match     — assess at most 3 new postings         (~$0.06)
  3. validate  — check the validator fired correctly   (free)
  4. research  — one company report with sources       (~$0.05)
  5. render    — rebuild the newspaper and verify it   (free)

Estimated total: about $0.11, hard-capped at $0.25.

Run it for real with:
    ./scripts/smoke-test.sh --i-will-pay
DRY
  exit 0
fi

say "1. Capping spend for the duration of this test"
exec_in python3 - <<'PY'
import json, shutil
shutil.copy("/app/config.json", "/data/config.smoke-backup.json")
c = json.load(open("/app/config.json"))
c["matching"]["max_jobs_per_day"] = 3
c["matching"]["max_usd_per_day"] = 0.25
json.dump(c, open("/data/config.smoke.json", "w"), indent=2)
print(f"  cap: 3 assessments, $0.25")
PY
CFG=/data/config.smoke.json

restore(){ say "Restoring your configuration"; exec_in rm -f /data/config.smoke.json; }
trap restore EXIT

say "2. Discovery"
exec_in python3 /app/zhtimes/discover.py --config "$CFG" --push 2>&1 | tail -4
exec_in test -s /data/queue.json && ok "queue written" || no "no queue produced"

say "3. Assessment (max 3, validator active)"
exec_in python3 /app/zhtimes/match.py --config "$CFG" --limit 3 2>&1 | tail -8

say "4. Checking what was produced"
exec_in python3 - <<'PY'
import json, sys
rows = [json.loads(l) for l in open("/data/assessments.jsonl")]
scored = [r for r in rows if r.get("score") is not None]
print(f"  assessments on file: {len(scored)}")
if not scored:
    print("  FAIL no assessment produced"); sys.exit(1)
r = scored[-1]
checks = {
    "has a SCORES line":        "SCORES:" in (r.get("matchText") or ""),
    "has a VERDICT line":       "VERDICT:" in (r.get("matchText") or ""),
    "has a competency table":   "Core Competencies" in (r.get("matchText") or ""),
    "records the prompt version": bool(r.get("prompt_version")),
    "records cost":             r.get("usd") is not None,
    "verdict parsed":           r.get("verdict") in ("apply", "explore", "skip"),
}
for k, v in checks.items():
    print(f"  {'PASS' if v else 'FAIL'}  {k}")
dg = [x for x in scored if x.get("downgraded")]
print(f"  validator downgrades in this run: {len(dg)}"
      + (f" (e.g. {dg[0]['model_recommendation']}/{dg[0]['model_score']}"
         f" -> {dg[0]['recommendation']}/{dg[0]['score']})" if dg else ""))
sys.exit(0 if all(checks.values()) else 1)
PY
[ $? -eq 0 ] && ok "assessment structure is valid" || no "assessment structure invalid"

say "5. Research (1 company)"
exec_in python3 /app/zhtimes/research.py --config "$CFG" --limit 1 2>&1 | tail -4
exec_in python3 -c "
import json,sys
rows=[json.loads(l) for l in open('/data/research.jsonl')]
done=[r for r in rows if r.get('research')]
print(f'  research reports: {len(done)}')
sys.exit(0 if done and 'http' in done[-1]['research'] else 1)" \
  && ok "research produced a report with source links" || no "research produced nothing usable"

say "6. Newspaper"
exec_in python3 /app/zhtimes/report.py --config "$CFG" 2>&1 | tail -4
exec_in python3 -c "
import pathlib,sys
t=pathlib.Path('/data/www/index.html').read_text()
c={'masthead':'The ZeroHour Times' in t,'notices':t.count('details class=\"ad\"')>0,
   'verdict badges':'class=\"b b-' in t,'links':'Original notice' in t}
[print(f'  {\"PASS\" if v else \"FAIL\"}  {k}') for k,v in c.items()]
sys.exit(0 if all(c.values()) else 1)" \
  && ok "newspaper rendered with real jobs" || no "newspaper did not render correctly"

say "7. Spend"
exec_in python3 -c "
import json;d=json.load(open('/data/spend.json'))
print(f\"  spent \${d['usd']:.4f} over {d['calls']} calls (cap \$0.25)\")"

say "Result"
printf '  %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] && printf '\n\033[32mSmoke test PASSED — the full pipeline works end to end.\033[0m\n' \
                 || printf '\n\033[31mSmoke test FAILED — see above.\033[0m\n'
exit "$fail"
