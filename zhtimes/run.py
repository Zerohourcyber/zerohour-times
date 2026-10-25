#!/usr/bin/env python3
"""Entry point: serve the dashboard and run the daily pipeline.

Replaces the systemd timers used on a host install, so the whole thing works
inside one container with no scheduler to configure. Still stdlib only.

    run.py              serve the dashboard and run the pipeline daily
    run.py once         run the pipeline once and exit
    run.py serve        serve the dashboard only
    run.py demo         build the dashboard from bundled sample data and serve it

The stages are deliberately independent: discovery, matching and research each
run in their own subprocess, a failure in one does not stop the others, and the
dashboard is rebuilt either way so a failure is visible on the page rather than
silently absent.
"""

import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as S

HERE = os.path.dirname(os.path.abspath(__file__))


def stage(script, *args, required=False):
    """Run one stage. Returns True on success. Never raises for an optional stage."""
    cmd = [sys.executable, os.path.join(HERE, script), "--config", S.CONFIG_PATH, *args]
    print(f"\n=== {script} {' '.join(args)}", flush=True)
    try:
        rc = subprocess.call(cmd)
    except OSError as e:
        print(f"!!! {script} could not start: {e}", file=sys.stderr, flush=True)
        return False
    if rc != 0:
        print(f"!!! {script} exited {rc}"
              f"{' (required)' if required else ' — continuing'}", file=sys.stderr, flush=True)
    return rc == 0


def pipeline():
    started = datetime.now(ZoneInfo(S.TZ_NAME))
    print(f"\n######## pipeline {started.strftime('%Y-%m-%d %H:%M %Z')}", flush=True)
    if not S.MCP_TOKEN:
        print("JOBSYNC_MCP_TOKEN is not set — skipping discovery and matching.\n"
              "Mint one in JobSync: Settings -> MCP (scope: jobs:write), then put it in .env.",
              file=sys.stderr, flush=True)
    else:
        stage("discover.py", "--push")
        stage("match.py")
        if S.OPENAI_API_KEY:
            stage("research.py", "--limit", "3")
        else:
            print("OPENAI_API_KEY is not set — skipping research.", file=sys.stderr, flush=True)
    # Always rebuild: a failed stage must show on the page, not vanish.
    stage("report.py", required=True)


def next_run(now):
    hh, _, mm = S.DAILY_RUN_AT.partition(":")
    target = now.replace(hour=int(hh), minute=int(mm or 0), second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


def serve():
    os.makedirs(S.WWW_DIR, exist_ok=True)
    handler = partial(SimpleHTTPRequestHandler, directory=S.WWW_DIR)
    httpd = ThreadingHTTPServer((S.DASHBOARD_BIND, S.DASHBOARD_PORT), handler)
    print(f"dashboard on http://{S.DASHBOARD_BIND}:{S.DASHBOARD_PORT}  "
          f"(read-only, UNAUTHENTICATED — do not expose publicly)", flush=True)
    httpd.serve_forever()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"

    if mode == "once":
        pipeline()
        return 0
    if mode == "serve":
        serve()
        return 0
    if mode == "demo":
        os.environ.setdefault("ZHT_STATE_DIR", os.path.join(os.path.dirname(HERE), "samples", "state"))
        stage("report.py", required=True)
        serve()
        return 0

    threading.Thread(target=serve, daemon=True).start()
    if os.environ.get("ZHT_RUN_ON_START", "1") == "1":
        pipeline()
    while True:
        now = datetime.now(ZoneInfo(S.TZ_NAME))
        nxt = next_run(now)
        secs = (nxt - now).total_seconds()
        print(f"\nnext run {nxt.strftime('%Y-%m-%d %H:%M %Z')} "
              f"(in {secs/3600:.1f}h)", flush=True)
        time.sleep(secs)
        pipeline()


if __name__ == "__main__":
    sys.exit(main())
