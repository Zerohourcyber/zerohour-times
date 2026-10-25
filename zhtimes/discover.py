#!/usr/bin/env python3
"""JobSync discovery — increment 1: fetch, normalise, filter, dedupe.

Pulls open roles from public ATS boards (Greenhouse, Lever, Ashby), normalises
them into the exact shape JobSync's MCP `add_jobs_batch` accepts, and prints
what it would send. `--push` sends it; the default is a dry run.

Design notes that are load-bearing, not decoration:

  * JobSync's `add_job` resolves company, job title, location and source BY NAME.
    Its cross-source dedupe is `companyId + jobTitleId` inside a 30-day window
    (MCP_DUPLICATE_WINDOW_DAYS), so "Stripe" and "Stripe, Inc." become two
    companies and the dedupe silently stops working. canonical_company() is
    therefore the most correctness-critical function in this file.
  * JobSync upserts, so we do not need our own job store. We keep only a
    watchlist. No database.
  * Stdlib only — this runs from cron next to the backup script, not in a venv.

Not yet implemented (later increments): employer discovery via an aggregator,
token resolution into the watchlist, USAJOBS.
"""

import argparse, json, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as S
TIMEOUT = 25

# ---------------------------------------------------------------- fetching

def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)

def fetch_greenhouse(token):
    # content=true returns the description, which JobSync wants for matching.
    d = _get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
    for j in d.get("jobs", []):
        yield {
            "title": j.get("title"),
            "url": j.get("absolute_url"),
            "location": (j.get("location") or {}).get("name"),
            "description": j.get("content"),
            "posted": j.get("updated_at") or j.get("first_published"),
        }

def fetch_lever(token):
    d = _get(f"https://api.lever.co/v0/postings/{token}?mode=json")
    for j in d:
        cat = j.get("categories") or {}
        yield {
            "title": j.get("text"),
            "url": j.get("hostedUrl"),
            "location": cat.get("location"),
            "description": j.get("descriptionPlain") or j.get("description"),
            "posted": j.get("createdAt"),
            "commitment": cat.get("commitment"),
            "workplace": j.get("workplaceType"),
        }

def fetch_ashby(token):
    d = _get(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=false")
    for j in d.get("jobs", []):
        yield {
            "title": j.get("title"),
            "url": j.get("jobUrl"),
            "location": j.get("location"),
            "description": j.get("descriptionPlain") or j.get("descriptionHtml"),
            "posted": j.get("publishedAt"),
            "commitment": j.get("employmentType"),
            # NOT j["isRemote"]: on 2026-10-23 OpenAI had 527 postings flagged
            # isRemote=true of which 325 were located "San Francisco". The flag
            # means remote-friendly, not remote. The location string is the signal.
            "workplace": None,
        }

BOARDS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby}

# ------------------------------------------------------------ normalising

_SUFFIXES = re.compile(
    r",?\s+(inc|inc\.|llc|l\.l\.c\.|ltd|ltd\.|limited|corp|corp\.|corporation|co|co\.|"
    r"gmbh|plc|sa|nv|bv|ab|oy|pty|pte|holdings|group|labs|technologies|technology)\b\.?",
    re.I,
)

def canonical_company(name):
    """One company must always produce one string, or JobSync's dedupe breaks.

    Keeps the display casing people expect but strips the legal-entity noise
    that makes the same employer arrive under several names from two sources.
    """
    if not name:
        return None
    s = re.sub(r"\s+", " ", str(name)).strip().strip(",.|-–— ")
    prev = None
    while prev != s:                      # "Foo Technologies, Inc." -> "Foo"
        prev = s
        s = _SUFFIXES.sub("", s).strip().strip(",.|-–— ")
    return s or None

def canonical_title(title):
    if not title:
        return None
    s = re.sub(r"\s+", " ", str(title)).strip()
    s = re.sub(r"\s*[\(\[][^)\]]*(remote|hybrid|onsite|contract|us|usa)[^)\]]*[\)\]]", "", s, flags=re.I)
    s = re.sub(r"\s*[-–—|]\s*(remote|hybrid|onsite)\b.*$", "", s, flags=re.I)
    s = re.sub(r"\s*[-–—|,]\s*(us|usa|united states|remote[- ]us)\s*$", "", s, flags=re.I)
    return s.strip().strip("-–—|,").strip() or None

def normalize_url(url):
    """Mirror the sink's intent: same posting, same key, regardless of tracking."""
    if not url:
        return None
    p = urllib.parse.urlsplit(url.strip())
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query)
         if not k.lower().startswith(("utm_", "gh_", "lever-"))]
    path = p.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), path,
                                    urllib.parse.urlencode(q), ""))

REMOTE_RE = re.compile(r"\bremote\b|\bwork from home\b|\bdistributed\b|\banywhere\b", re.I)
HYBRID_RE = re.compile(r"\bhybrid\b", re.I)

def workplace_type(raw, location, description):
    """Explicit board field first, then the location string. Never the description.

    Scanning the description for "remote" produced false positives on every
    board tested — job bodies discuss remote policy, relocation and hybrid
    expectations regardless of where the role actually sits. A wrong Remote
    label is worse than none: it is the filter the whole search depends on.
    """
    if raw:
        r = raw.strip().lower()
        if r in ("remote",):
            return "Remote"
        if r in ("hybrid",):
            return "Hybrid"
        if r in ("onsite", "on-site", "on site"):
            return "Onsite"
    loc = location or ""
    if HYBRID_RE.search(loc):
        return "Hybrid"
    if REMOTE_RE.search(loc):
        return "Remote"
    return "Onsite" if loc.strip() else None

def job_type(commitment):
    """Only the three spellings the MCP schema documents: Full-time, Part-time, Contract.

    Anything else is sent as nothing rather than guessed — a value outside the
    set is either rejected or quietly resolved into a junk lookup row.
    """
    if not commitment:
        return None
    c = commitment.lower()
    if "intern" in c:
        return None
    if "part" in c:
        return "Part-time"
    if "contract" in c or "temporary" in c or "contractor" in c:
        return "Contract"
    if "full" in c:
        return "Full-time"
    return None

def strip_html(s, limit=12000):
    if not s:
        return None
    s = urllib.parse.unquote(str(s))
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</li>|</h[1-6]>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                 ("&#39;", "'"), ("&nbsp;", " "), ("&rsquo;", "'"), ("&mdash;", "—")):
        s = s.replace(a, b)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    return s.strip()[:limit] or None

# ---------------------------------------------------------------- filtering

def matches(job, flt):
    title = (job.get("jobTitle") or "").lower()
    if flt.get("titleAny") and not any(k.lower() in title for k in flt["titleAny"]):
        return False, "title"
    if flt.get("titleNone") and any(k.lower() in title for k in flt["titleNone"]):
        return False, "excluded-title"
    if flt.get("remoteOnly") and job.get("workplaceType") != "Remote":
        return False, "not-remote"
    loc = (job.get("location") or "").lower()
    # US indicators win over the deny-list. Postings are routinely listed across
    # several countries at once ("Remote, Canada; Remote, United States"), and a
    # plain deny-list throws those away even though they are US-eligible — which
    # silently loses some of the strongest matches.
    us = flt.get("locationAny") or []
    if us and any(k.lower() in loc for k in us):
        return True, None
    if flt.get("locationNone") and any(k.lower() in loc for k in flt["locationNone"]):
        return False, "excluded-location"
    if us:
        return False, "no-us-signal"
    return True, None



# ---------------------------------------------------------- logging / alerts

LOG_FILE = os.environ.get("ZHT_LOG_FILE", f"{S.STATE_DIR}/zerohour-times.log")
STATE_DIR = S.STATE_DIR
SEEN_FILE = f"{STATE_DIR}/seen.json"
QUEUE_FILE = f"{STATE_DIR}/queue.json"

# JobSync allows MCP_RATE_LIMIT_MAX=100 calls per hour per token. A find_job per
# kept posting scales with the WATCHLIST, not with new postings, so at 150
# employers it would spend the entire budget before pushing anything. The seen
# set makes calls scale with genuinely-new postings instead. It is a JSON file,
# not a database: if it is lost the worst case is one wasted find_job per job.
# Discovery and matching share JobSync's 100-calls/hour MCP ceiling, and the
# pipeline runs discovery FIRST. With a large watchlist discovery could spend the
# whole budget pushing, leaving matching to fail every lookup and assess nothing —
# which is exactly what happened on 2026-10-24 with 119 employers. Discovery is
# therefore capped at roughly half, leaving headroom for the stage behind it.
MCP_CALL_BUDGET = S.MCP_CALL_BUDGET


def load_seen(path=SEEN_FILE):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def save_seen(seen, path=SEEN_FILE):
    try:
        import os
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(path, "w") as fh:
            json.dump(seen, fh, indent=0, sort_keys=True)
    except OSError as e:
        print(f"# WARN could not write seen set: {e}", file=sys.stderr)

def log_line(path, text):
    """Append-only, one line per run. Never raises: a logging failure must not
    fail the run, and a cron job that dies while logging reports nothing."""
    try:
        with open(path, "a") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {text}\n")
    except OSError as e:
        print(f"# WARN could not write {path}: {e}", file=sys.stderr)

def write_state(summary):
    """Last-run status, for a dashboard tile or an eyeball. Best effort."""
    try:
        import os
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(f"{STATE_DIR}/last-run.json", "w") as fh:
            json.dump(summary, fh, indent=2)
    except OSError as e:
        print(f"# WARN could not write state: {e}", file=sys.stderr)

def notify(webhook, summary):
    """POST a failure to an existing n8n webhook. Optional by design.

    There is no MTA on this host and installing one for a cron job is more
    infrastructure than the problem deserves. n8n already runs here, so a
    webhook reuses what exists. With no webhook configured the run is still
    visible: the log line, last-run.json and a non-zero exit code.
    """
    if not webhook:
        return
    try:
        req = urllib.request.Request(
            webhook, data=json.dumps(summary).encode(), method="POST",
            headers={"Content-Type": "application/json", "User-Agent": UA})
        urllib.request.urlopen(req, timeout=15).read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        print(f"# WARN notification failed: {e}", file=sys.stderr)

# ------------------------------------------------------------------- push

MCP_URL = S.MCP_URL
BATCH_MAX = 10          # add_jobs_batch declares maxItems: 10

def read_token(path=None):
    """Token from JOBSYNC_MCP_TOKEN / _FILE, or an explicit path for tests."""
    if path:
        with open(path) as fh:
            return fh.read().strip()
    if not S.MCP_TOKEN:
        raise RuntimeError("JOBSYNC_MCP_TOKEN is not set — see .env.example")
    return S.MCP_TOKEN

def _rpc(token, method, params, req_id=1):
    body = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}).encode()
    req = urllib.request.Request(MCP_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        # The endpoint is a Streamable HTTP MCP server: it may answer with JSON
        # or with an SSE frame, so accept both and unwrap below.
        "Accept": "application/json, text/event-stream",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for line in raw.splitlines():
            if line.startswith("data:"):
                try:
                    return json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
        raise RuntimeError(f"unparseable MCP response: {raw[:300]}")

def to_mcp(job):
    """Map our normalised shape onto the tool's schema, which is strict.

    `jobDescription` is required, so a posting with no body is sent as 'N/A' —
    the schema's own instruction — rather than dropped. `upsert` is always true:
    the tool documents it as the setting for every re-run of a scheduled search,
    and it is what makes this safe to run on a cron.
    """
    out = {
        "company": job["company"],
        "jobTitle": job["jobTitle"],
        "jobDescription": job.get("description") or "N/A",
        "jobUrl": job["jobUrl"],
        "source": job.get("source"),
        "status": "new",
    }
    for key in ("location", "workplaceType", "jobType"):
        if job.get(key):
            out[key] = job[key]
    return {k: v for k, v in out.items() if v is not None}

def already_known(job, token, req_id):
    """Ask JobSync whether this posting is already saved, by URL.

    This exists because upsert rewrites every field it is given, statusId
    included. Discovery sends status="new", so re-pushing a posting the owner
    has already marked Applied would quietly reset it to New and erase their
    progress. Surfacing NEW postings is this service's job; re-pushing unchanged
    ones has no value and real downside, so by default we skip what is known.
    `--enrich` opts back into upsert for the cases where refreshing a stale
    description is actually wanted.
    """
    if not job.get("jobUrl"):
        return False
    try:
        resp = _rpc(token, "tools/call",
                    {"name": "find_job", "arguments": {"jobUrl": job["jobUrl"]}},
                    req_id=req_id)
    except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, TimeoutError):
        return False        # fail open: a failed check must not drop a new posting
    text = " ".join(b.get("text", "") for b in (resp.get("result") or {}).get("content", []))
    low = text.lower()
    if "not found" in low or "no job" in low or "nothing" in low:
        return False
    return "found" in low or "already" in low or "id:" in low


def push(jobs, token, dry=False, enrich=False):
    sent = {"batches": 0, "created": 0, "updated": 0, "other": 0, "skipped": 0,
            "calls": 0, "rate_limited": False, "errors": []}
    seen = load_seen()

    if not enrich:
        fresh, rid = [], 1000
        for j in jobs:
            url = j.get("jobUrl")
            if url and url in seen:
                sent["skipped"] += 1          # known locally: costs no MCP call
                continue
            if sent["calls"] >= MCP_CALL_BUDGET:
                sent["errors"].append(
                    f"call budget ({MCP_CALL_BUDGET}) reached before checking "
                    f"{len(jobs) - len(fresh) - sent['skipped']} posting(s) — they will be "
                    f"picked up on the next run")
                break
            rid += 1
            sent["calls"] += 1
            if already_known(j, token, rid):
                sent["skipped"] += 1
                if url:
                    seen[url] = datetime.now(timezone.utc).date().isoformat()
                print(f"    known, skipping: {j['company']} — {j['jobTitle']}")
            else:
                fresh.append(j)
        jobs = fresh

    for i in range(0, len(jobs), BATCH_MAX):
        chunk = [to_mcp(j) for j in jobs[i:i + BATCH_MAX]]
        if enrich:
            # Only here do we let JobSync rewrite an existing row.
            for item in chunk:
                item["upsert"] = True
                item.pop("status", None)   # never reassert status on an existing job
        sent["batches"] += 1
        sent["calls"] += 1
        if dry:
            continue
        if sent["calls"] > MCP_CALL_BUDGET:
            sent["errors"].append("call budget reached mid-push — remaining batches deferred")
            break
        try:
            resp = _rpc(token, "tools/call",
                        {"name": "add_jobs_batch", "arguments": {"jobs": chunk}},
                        req_id=sent["batches"])
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, TimeoutError) as e:
            sent["errors"].append(f"batch {sent['batches']}: {e}")
            continue
        if resp.get("error"):
            sent["errors"].append(f"batch {sent['batches']}: {resp['error']}")
            continue
        # One content block can carry every item in the batch, labelled [n/total],
        # so count outcomes in the text rather than counting blocks.
        text = "\n".join(b.get("text", "") for b in (resp.get("result") or {}).get("content", []))
        for line in (ln.strip() for ln in text.splitlines() if ln.strip()):
            print("    " + line[:200])
        created = len(re.findall(r"\bjob created\b", text, re.I))
        updated = len(re.findall(r"\bupdated\b", text, re.I))
        items = len(re.findall(r"\[\d+/\d+\]", text)) or len(chunk)
        sent["created"] += created
        sent["updated"] += updated
        sent["other"] += max(0, items - created - updated)
        # A rate-limited batch silently drops postings. Treating it as success
        # means a run can lose a day of discoveries and still report ok=True.
        if re.search(r"rate limit exceeded", text, re.I):
            wait = re.search(r"try again in (\d+)s", text, re.I)
            sent["errors"].append(
                f"batch {sent['batches']}: MCP rate limit hit"
                + (f", resets in {wait.group(1)}s" if wait else "")
                + " — postings in this batch were NOT saved")
            sent["rate_limited"] = True
    return sent

# ------------------------------------------------------------------- main

def collect(watchlist, flt, verbose=False):
    seen, out, stats = {}, [], {"fetched": 0, "kept": 0, "dupe": 0, "errors": []}
    for entry in watchlist:
        board, token = entry["board"], entry["token"]
        company = entry.get("company") or token
        try:
            raw = list(BOARDS[board](token))
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError, TimeoutError) as e:
            stats["errors"].append(f"{board}/{token}: {e}")
            continue
        stats["fetched"] += len(raw)
        for r in raw:
            desc = strip_html(r.get("description"))
            job = {
                "jobTitle": canonical_title(r.get("title")),
                "company": canonical_company(company),
                "jobUrl": normalize_url(r.get("url")),
                "location": (r.get("location") or "").strip() or None,
                "workplaceType": workplace_type(r.get("workplace"), r.get("location"), desc),
                "jobType": job_type(r.get("commitment")),
                "description": desc,
            }
            if not (job["jobTitle"] and job["company"] and job["jobUrl"]):
                continue
            ok, why = matches(job, flt)
            if not ok:
                if verbose:
                    print(f"    skip [{why}] {job['company']} — {job['jobTitle']}", file=sys.stderr)
                continue
            # Local dedupe mirrors the sink's rule so we never send a pair that
            # JobSync would collapse anyway.
            key = (job["company"].lower(), job["jobTitle"].lower())
            if key in seen or job["jobUrl"] in seen:
                stats["dupe"] += 1
                continue
            seen[key] = seen[job["jobUrl"]] = True
            job["_source"] = f"{board}/{token}"
            job["source"] = board.capitalize()   # schema wants a board name
            out.append(job)
    stats["kept"] = len(out)
    return out, stats

def main():
    ap = argparse.ArgumentParser(description="JobSync discovery — increment 1")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--push", action="store_true", help="send to JobSync (default: dry run)")
    ap.add_argument("--limit", type=int, default=0, help="cap jobs sent/printed")
    ap.add_argument("--token-file", default=None,
                    help="read the MCP token from this file instead of the environment")
    ap.add_argument("--log", default=LOG_FILE)
    ap.add_argument("--enrich", action="store_true",
                    help="refresh postings JobSync already has (upsert). Off by default: "
                         "upsert rewrites statusId, which would reset an Applied job to New")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    cfg = json.load(open(a.config))
    jobs, stats = collect(cfg["watchlist"], cfg.get("filters", {}), a.verbose)
    if a.limit:
        jobs = jobs[: a.limit]

    print(f"# {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"# fetched={stats['fetched']} kept={stats['kept']} local-dupes={stats['dupe']}")
    for e in stats["errors"]:
        print(f"# ERROR {e}", file=sys.stderr)
    for j in jobs:
        print(f"  [{j['_source']:22}] {j['company']} — {j['jobTitle']}"
              f"  ({j.get('workplaceType') or 'unspecified'}; {j.get('location') or 'no location'})")

    if not a.push:
        return 0

    try:
        token = read_token(a.token_file)
    except OSError as e:
        print(f"\ncannot read the MCP token: {e}", file=sys.stderr)
        return 2
    print(f"\n# pushing {len(jobs)} job(s) to JobSync in batches of {BATCH_MAX}")
    sent = push(jobs, token, enrich=a.enrich)
    print(f"# batches={sent['batches']} created={sent['created']} "
          f"updated={sent['updated']} other={sent['other']} skipped={sent['skipped']}")
    for e in sent["errors"]:
        print(f"# ERROR {e}", file=sys.stderr)

    # Hand the day's candidates to the matcher. Written even when nothing new was
    # pushed, because a posting already in JobSync may still be unscored.
    try:
        import os
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(QUEUE_FILE, "w") as fh:
            json.dump({j["jobUrl"]: j for j in jobs if j.get("jobUrl")}, fh, indent=0)
        print(f"# queued {len(jobs)} posting(s) for matching -> {QUEUE_FILE}")
    except OSError as e:
        print(f"# WARN could not write the match queue: {e}", file=sys.stderr)

    summary = {
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "companies": len(cfg["watchlist"]),
        "fetched": stats["fetched"],
        "kept": stats["kept"],
        "created": sent["created"],
        "updated": sent["updated"],
        "skipped": sent["skipped"],
        "mcp_calls": sent["calls"],
        "rate_limited": sent["rate_limited"],
        "fetch_errors": stats["errors"],
        "push_errors": sent["errors"],
        "ok": not (sent["errors"] or stats["errors"]),
    }
    log_line(a.log, (f"companies={summary['companies']} fetched={summary['fetched']} "
                     f"kept={summary['kept']} created={summary['created']} "
                     f"skipped={summary['skipped']} mcp_calls={summary['mcp_calls']} "
                     f"fetch_errors={len(stats['errors'])} push_errors={len(sent['errors'])} "
                     f"ok={summary['ok']}"))
    write_state(summary)
    if not summary["ok"]:
        notify(cfg.get("notify_webhook"), summary)
    return 1 if sent["errors"] else 0

if __name__ == "__main__":
    sys.exit(main())
