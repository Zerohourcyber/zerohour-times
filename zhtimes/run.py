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


PLACEHOLDER = """<!doctype html><meta charset="utf-8">
<title>The ZeroHour Times</title>
<style>body{background:#f4f1ea;color:#1a1a1a;font-family:Georgia,serif;margin:0;
display:grid;place-items:center;height:100vh;text-align:center}
h1{font-size:2.2rem;letter-spacing:.02em;border-bottom:3px double #1a1a1a;padding-bottom:.3em}
p{max-width:34rem;line-height:1.6}code{background:#e6e1d6;padding:.15em .4em}</style>
<div><h1>The ZeroHour Times</h1>
<p>No edition has been printed yet. The front page appears once the pipeline has
run at least once &mdash; <code>docker compose logs -f zerohour-times</code> to
watch it, or <code>docker compose exec zerohour-times python3 /app/zhtimes/run.py once</code>
to run it now.</p></div>
"""


class Dashboard(SimpleHTTPRequestHandler):
    """Serves the report and nothing else.

    SimpleHTTPRequestHandler lists the directory when index.html is missing,
    which turned a failed render into a file listing of our state directory.
    """

    def list_directory(self, path):
        self.send_error(404, "No edition yet")
        return None

    def log_message(self, fmt, *args):
        # log_error() passes an int first, so index nothing and format nothing:
        # a raised TypeError in here would kill the request thread.
        if "200" not in " ".join(str(a) for a in args):
            super().log_message(fmt, *args)


def serve():
    os.makedirs(S.WWW_DIR, exist_ok=True)
    index = os.path.join(S.WWW_DIR, "index.html")
    if not os.path.exists(index):
        with open(index, "w") as fh:
            fh.write(PLACEHOLDER)
    handler = partial(Dashboard, directory=S.WWW_DIR)
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
        # setdefault() never fired: the image already sets ZHT_STATE_DIR=/data,
        # so demo mode read an empty state dir and rendered nothing. settings is
        # imported above, so this process's own copy has to be corrected too —
        # report.py runs as a subprocess and picks the paths up from the env.
        state = os.path.join(os.path.dirname(HERE), "samples", "state")
        os.environ["ZHT_STATE_DIR"] = S.STATE_DIR = state
        os.environ["ZHT_WWW_DIR"] = S.WWW_DIR = os.path.join(state, "www")
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
