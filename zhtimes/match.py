#!/usr/bin/env python3
"""JobSync matching — score discovered postings and write a daily shortlist.

Runs independently of discovery: discovery never calls an LLM, and an AI failure
here can never interrupt or corrupt discovery. The hand-off is a queue file.

Contract with JobSync (all through the published MCP interface, never the DB):
  * find_job            -> the jobId, and whether a match already exists
  * save_match_results_batch -> persists the analysis, 10 at a time
  * matchText must begin with
        SCORES: match=<0-100> recommendation=<strong|good|partial|weak>
    which JobSync parses, clamps and strips before storing the markdown body.

Safety properties, in order of how much they matter:
  1. Never overwrites an existing assessment without --force. JobSync stores one
     match per job (matchScore/matchData are columns, there is no history table),
     so a careless re-run destroys prior analysis irreversibly.
  2. Never invents. The prompt forbids it and the profile carries provenance, but
     the daily spend cap and the "unknown stays unknown" rule are what keep a
     plausible-sounding fabrication from being written into the tracker at scale.
  3. Bounded everything: per-call timeout, bounded retries with backoff, a daily
     call cap and a daily dollar cap, both keyed on the local date (ZHT_TZ).
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as S

import argparse, json, os, pathlib, re, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

STATE_DIR = S.STATE_DIR
QUEUE_FILE = f"{STATE_DIR}/queue.json"
EXTERNAL_FILE = f"{STATE_DIR}/externally-scored.json"
SPEND_FILE = f"{STATE_DIR}/spend.json"
ASSESS_LOG = f"{STATE_DIR}/assessments.jsonl"
MCP_URL = S.MCP_URL
MCP_TOKEN_FILE = None   # token comes from the environment; see settings.py
OPENAI_KEY_FILE = None
OPENAI_URL = S.OPENAI_CHAT
TZ = ZoneInfo(S.TZ_NAME)             # all user-facing dates and scheduling
UA = S.USER_AGENT

SCORES_RE = re.compile(
    r"SCORES:\s*match=(\d+)\s+recommendation=(strong|good|partial|weak)", re.I)


def today_local():
    return datetime.now(TZ).date().isoformat()


def read_secret(path):
    """A path reads that file; None means take it from the environment."""
    if path:
        with open(path) as fh:
            return fh.read().strip()
    raise RuntimeError("no secret path given")


# ------------------------------------------------------------------ MCP

def mcp(token, name, arguments, req_id=1, timeout=60):
    body = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                       "params": {"name": name, "arguments": arguments}}).encode()
    req = urllib.request.Request(MCP_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        d = next((json.loads(l[5:].strip()) for l in raw.splitlines()
                  if l.startswith("data:")), None)
        if d is None:
            raise RuntimeError(f"unparseable MCP response: {raw[:200]}")
    if d.get("error"):
        raise RuntimeError(str(d["error"])[:200])
    return " ".join(b.get("text", "") for b in (d.get("result") or {}).get("content", []))


def lookup(token, url, req_id):
    """jobId + whether a match already exists, from find_job's own report."""
    text = mcp(token, "find_job", {"jobUrl": url}, req_id)
    if "rate limit exceeded" in text.lower():
        raise RuntimeError("MCP rate limit")
    m = re.search(r"id:\s*([0-9a-f-]{36})", text)
    if not m:
        return None, None, text
    scored = not re.search(r"match:\s*not scored", text, re.I)
    return m.group(1), scored, text


# --------------------------------------------------------------- OpenAI

def openai_call(key, model, system, user, timeout, max_tokens, retries, backoff):
    """Bounded retries. 4xx other than 429 are not retried: a bad request will
    stay bad, and retrying it just spends the budget twice."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }).encode()
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(OPENAI_URL, data=payload, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json",
            "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.load(r)
            return d["choices"][0]["message"]["content"], d.get("usage", {})
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            last = f"HTTP {e.code}: {body}"
            if e.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
            last = f"{type(e).__name__}: {e}"
        if attempt < retries:
            time.sleep(backoff * (2 ** attempt))
    raise RuntimeError(last or "openai call failed")


def cost_of(usage, cfg):
    ins = usage.get("prompt_tokens", 0)
    outs = usage.get("completion_tokens", 0)
    return round(ins / 1000 * cfg["usd_per_1k_input"]
                 + outs / 1000 * cfg["usd_per_1k_output"], 6)



# -------------------------------------------------------------- validation

BANDS = {"strong": (80, 100), "good": (60, 79), "partial": (40, 59), "weak": (0, 39)}
ORDER_REC = ["weak", "partial", "good", "strong"]
VALID_STATUS = {"demonstrated", "transferable", "not documented", "confirmed gap"}
ELIG_STATUS = {"met", "not met", "unverifiable"}
VERDICT_RE = re.compile(r"VERDICT:\s*(apply|explore|skip)", re.I)
# Titles an employer has reserved for entrants. Checked deterministically: the
# title is reliable for this and does not depend on the model noticing.
JUNIOR_TITLE_RE = re.compile(
    r"\b(intern|internship|co-?op|apprentice|new ?grad|graduate programme|graduate program|"
    r"entry[- ]level|junior|jr\.?)\b", re.I)
PREF_RE = re.compile(
    r"PREFERENCE:\s*desirability=(high|medium|low)\s+direction=(advances|lateral|diverges)", re.I)


def _cells(line):
    if not line.strip().startswith("|"):
        return None
    parts = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(parts) < 3 or all(set(c) <= set("-: ") for c in parts):
        return None
    return parts


def parse_competencies(text):
    """Parse the competency table, tolerating the v2 (5-col) and v3 (6-col) shapes.

    Columns are located by content rather than position: the status cell is the
    one holding one of the four allowed values. A table that cannot be parsed is
    an error, because the model's score is only trustworthy insofar as it can be
    checked against structured claims.
    """
    rows = []
    for line in text.splitlines():
        parts = _cells(line)
        if not parts:
            continue
        lower = [c.lower() for c in parts]
        if "status" in lower or "competency" in lower:
            continue
        status_i = next((i for i, c in enumerate(lower) if c in VALID_STATUS), None)
        yesno = [i for i, c in enumerate(lower) if c in ("yes", "no")]
        if status_i is None or not yesno:
            continue
        # v5 emits Defining then Critical; v2-v4 emit Critical alone.
        if len(yesno) >= 2:
            def_i, crit_i = yesno[0], yesno[1]
        else:
            def_i, crit_i = None, yesno[0]
        found_i = next((i for i, c in enumerate(lower)
                        if c in ("foundational", "learnable")), None)
        name = parts[1] if len(parts) > 1 and parts[0].isdigit() else parts[0]
        rows.append({
            "competency": name,
            "critical": lower[crit_i] == "yes",
            "defining": (lower[def_i] == "yes") if def_i is not None else None,
            "foundational": (lower[found_i] == "foundational") if found_i is not None else None,
            "status": lower[status_i],
            "evidence": parts[-1],
        })
    if not rows:
        return rows, "no parseable Core Competencies table in the model output"
    if not any(r["critical"] for r in rows):
        return rows, "no competency was marked critical — cannot validate the recommendation"
    return rows, None


def parse_eligibility(text):
    """Mandatory eligibility rows. Absent table is tolerated; a posting may state none."""
    rows = []
    for line in text.splitlines():
        parts = _cells(line)
        if not parts:
            continue
        lower = [c.lower() for c in parts]
        if "status" in lower or "requirement" in lower:
            continue
        i = next((j for j, c in enumerate(lower) if c in ELIG_STATUS), None)
        if i is None:
            continue
        # Skip competency rows, which also carry a yes/no and a four-value status.
        if any(c in VALID_STATUS for c in lower):
            continue
        rows.append({"requirement": parts[0], "stated_as": parts[1] if len(parts) > 2 else "",
                     "status": lower[i]})
    return rows


def validate(score, recommendation, rows, elig, title=""):
    """Enforce the constraints in code. Returns (score, recommendation, note).

    Ceilings, per the owner's rule:
      * mandatory eligibility Not Met -> weak (a skip; the candidate cannot be considered)
      * critical Confirmed Gap        -> at most partial
      * critical Not Documented       -> at most good
    """
    blocked = [e for e in elig if e["status"] == "not met"]
    if blocked:
        names = "; ".join(f"{e['requirement']}" for e in blocked)
        note = (f"**Automated skip.** The model returned `{recommendation}` / {score}, but a "
                f"mandatory eligibility requirement is not met: {names}. The candidate cannot be "
                f"considered for this posting regardless of qualification, so the validator set "
                f"`weak` / {min(score, BANDS['weak'][1])}.")
        return min(score, BANDS["weak"][1]), "weak", note

    if title and JUNIOR_TITLE_RE.search(title):
        ceiling = BANDS["partial"][1]
        if ORDER_REC.index(recommendation) > ORDER_REC.index("partial") or score > ceiling:
            note = (f"**Automated downgrade.** The model returned `{recommendation}` / {score}, but "
                    f"the posting title marks this as an internship or an explicitly junior role, "
                    f"which the employer has reserved for early-career candidates. Capped at "
                    f"`partial` / {min(score, ceiling)} regardless of how easily the work could be "
                    f"performed.")
            return min(score, ceiling), "partial", note

    gaps = [r for r in rows if r["critical"] and r["status"] == "confirmed gap"]
    # The DEFINING competency is the capability the job exists to apply. If it is
    # unevidenced the candidate would be learning the core of the role in post, so
    # it caps harder than any other critical competency.
    defining_undoc = [r for r in rows
                      if r.get("defining") and r["status"] == "not documented"]
    # A close mapping is worth applying on, but the candidate has not done the
    # thing the job exists to do. This closes the evasion where a Not Documented
    # competency is graded Transferable to clear the cap.
    defining_transfer = [r for r in rows
                         if r.get("defining") and r["status"] == "transferable"]
    undoc = [r for r in rows if r["critical"] and r["status"] == "not documented"
             and not r.get("defining")]
    if gaps:
        ceiling_rec, reason, offenders = "partial", "a confirmed gap", gaps
    elif defining_undoc:
        ceiling_rec, reason, offenders = (
            "partial", "the DEFINING competency and is not documented", defining_undoc)
    elif undoc:
        ceiling_rec, reason, offenders = "good", "not documented", undoc
    elif defining_transfer:
        ceiling_rec, reason, offenders = (
            "good", "the DEFINING competency and rests on transferable evidence rather than "
            "direct experience", defining_transfer)
    else:
        return score, recommendation, None

    ceiling = BANDS[ceiling_rec][1]
    if ORDER_REC.index(recommendation) > ORDER_REC.index(ceiling_rec) or score > ceiling:
        names = "; ".join(r["competency"] for r in offenders)
        note = (f"**Automated downgrade.** The model returned `{recommendation}` / {score}, but "
                f"{reason}: {names}. Capped at `{ceiling_rec}` / "
                f"{min(score, ceiling)} by the validator, not by the model.")
        return min(score, ceiling), ceiling_rec, note
    return score, recommendation, None


# ----------------------------------------------------------------- spend

def load_external(path=EXTERNAL_FILE):
    """URLs JobSync already has a match for that this pipeline did not create."""
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def save_external(data, path=EXTERNAL_FILE):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(path, "w") as fh:
            json.dump(data, fh, indent=0, sort_keys=True)
    except OSError as e:
        print(f"# WARN could not write {path}: {e}", file=sys.stderr)


def load_spend():
    try:
        with open(SPEND_FILE) as fh:
            d = json.load(fh)
        return d if d.get("date") == today_local() else {"date": today_local(), "calls": 0, "usd": 0.0}
    except (OSError, json.JSONDecodeError):
        return {"date": today_local(), "calls": 0, "usd": 0.0}


def save_spend(spend):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(SPEND_FILE, "w") as fh:
            json.dump(spend, fh, indent=2)
    except OSError as e:
        print(f"# WARN could not write spend state: {e}", file=sys.stderr)


def log_assessment(rec):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(ASSESS_LOG, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError as e:
        print(f"# WARN could not append to the assessment log: {e}", file=sys.stderr)


# ----------------------------------------------------------------- digest

def write_digest(path, results, cfg, spend):
    now = datetime.now(TZ)
    rank = {"apply": 0, "explore": 1, "skip": 2, None: 3}
    ranked = sorted([r for r in results if r.get("score") is not None],
                    key=lambda r: (rank.get(r.get("verdict"), 3), -r["score"]))
    lines = [
        f"# Job shortlist — {now.strftime('%A %d %B %Y, %H:%M %Z')}",
        "",
        f"Scored {len(ranked)} posting(s) with `{cfg['model']}` using prompt "
        f"`{cfg['prompt_version']}`. Estimated spend today: ${spend['usd']:.2f} "
        f"across {spend['calls']} call(s).",
        "",
    ]
    if not ranked:
        lines += ["Nothing new to score today.", ""]
    for r in ranked:
        lines += [
            f"## {(r.get('verdict') or 'no verdict').upper()} — {r['company']} · {r['jobTitle']}",
            "",
            f"- **Posting:** {r['url']}",
            f"- **Location / arrangement:** {r.get('location') or 'not stated'} · "
            f"{r.get('workplaceType') or 'not stated'}",
            f"- **Qualification:** {r['recommendation']} ({r['score']}) · "
            f"**Would want daily:** {r.get('desirability') or 'not stated'} · "
            f"**Career direction:** {r.get('direction') or 'not stated'}",
            "",
            r["body"].strip(),
            "",
            "---",
            "",
        ]
    failed = [r for r in results if r.get("error")]
    if failed:
        lines += ["## Not scored", ""]
        lines += [f"- {r['company']} · {r['jobTitle']} — {r['error']}" for r in failed] + [""]
    pathlib.Path(path).write_text("\n".join(lines))
    return path


# ------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Score discovered postings and write a shortlist")
    ap.add_argument("--config", default=S.CONFIG_PATH)
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be scored; no AI calls, no writes to JobSync")
    ap.add_argument("--limit", type=int, default=0, help="cap postings this run")
    ap.add_argument("--force", action="store_true",
                    help="re-score jobs that ALREADY have an assessment (destroys the previous one)")
    ap.add_argument("--prompt", help="override the prompt file (e.g. prompts/match-v2.md)")
    ap.add_argument("--queue", help="use an alternative queue file")
    ap.add_argument("--digest-only", action="store_true",
                    help="rebuild today's shortlist from the assessment log. No AI calls, no "
                         "JobSync writes — so a formatting failure can never cost paid work.")
    ap.add_argument("--calibrate", action="store_true",
                    help="score straight from the queue: no find_job lookup, no save, "
                         "nothing written to JobSync. For validation sets.")
    ap.add_argument("--no-save", action="store_true",
                    help="score and write the digest, but do not send results to JobSync")
    a = ap.parse_args()

    raw = json.load(open(a.config))
    cfg = raw.get("matching", {})
    cfg.setdefault("model", "gpt-4.1")
    cfg.setdefault("max_jobs_per_day", 40)
    cfg.setdefault("max_usd_per_day", 2.00)
    cfg.setdefault("timeout_seconds", 90)
    cfg.setdefault("max_tokens", 1600)
    cfg.setdefault("retries", 2)
    cfg.setdefault("retry_backoff_seconds", 3)
    cfg.setdefault("usd_per_1k_input", 0.002)
    cfg.setdefault("usd_per_1k_output", 0.008)
    cfg.setdefault("profile", S.PROFILE_PATH)
    cfg.setdefault("prompt", S.PROMPT_PATH)
    if a.prompt:
        cfg["prompt"] = a.prompt
    cfg.setdefault("digest_dir", STATE_DIR)
    cfg.setdefault("description_chars", 14000)

    if a.digest_only:
        # Rebuild from the append-only log rather than from this run's results.
        day = today_local()
        rows = []
        try:
            with open(ASSESS_LOG) as fh:
                for line in fh:
                    r = json.loads(line)
                    if r.get("local_date") == day and r.get("score") is not None:
                        rows.append({"company": r["company"], "jobTitle": r.get("jobTitle", "?"),
                                     "url": r["url"], "score": r["score"],
                                     "recommendation": r["recommendation"],
                                     "desirability": r.get("desirability"),
                                     "direction": r.get("direction"),
                                     "verdict": r.get("verdict"),
                                     "location": None, "workplaceType": None,
                                     "body": SCORES_RE.sub("", r.get("matchText", "")).strip()})
        except OSError as e:
            print(f"cannot read {ASSESS_LOG}: {e}", file=sys.stderr)
            return 2
        # Last assessment per URL wins, so a re-score supersedes an earlier one.
        dedup = {r["url"]: r for r in rows}
        spend = load_spend()
        cfg["prompt_version"] = "(digest rebuild)"
        out = write_digest(os.path.join(cfg["digest_dir"], f"digest-{day}.md"),
                           list(dedup.values()), cfg, spend)
        print(f"# rebuilt {out} from {len(dedup)} assessment(s) on {day}")
        return 0

    prompt = pathlib.Path(cfg["prompt"]).read_text()
    pv = re.search(r"prompt_version:\s*([a-z0-9.\-]+)", prompt)
    cfg["prompt_version"] = pv.group(1) if pv else pathlib.Path(cfg["prompt"]).stem
    profile = pathlib.Path(cfg["profile"]).read_text()

    queue_path = a.queue or QUEUE_FILE
    try:
        queue = json.load(open(queue_path))
    except (OSError, json.JSONDecodeError):
        print(f"no queue at {queue_path} — run discover.py first", file=sys.stderr)
        return 2

    token = read_secret(a.token_file) if a.token_file else S.MCP_TOKEN
    if not token:
        print("JOBSYNC_MCP_TOKEN is not set — see .env.example", file=sys.stderr)
        return 2
    spend = load_spend()
    budget_jobs = max(0, cfg["max_jobs_per_day"] - spend["calls"])
    if a.limit:
        budget_jobs = min(budget_jobs, a.limit)

    print(f"# {datetime.now(TZ).strftime('%Y-%m-%d %H:%M %Z')} | model={cfg['model']} "
          f"prompt={cfg['prompt_version']}")
    print(f"# queue={len(queue)} | budget: {budget_jobs} job(s), "
          f"${cfg['max_usd_per_day'] - spend['usd']:.2f} left today")

    external = load_external()
    todo, rid = [], 2000
    for url, posting in queue.items():
        if len(todo) >= budget_jobs:
            break
        if a.calibrate:
            # No lookup: calibration postings are deliberately never added to
            # JobSync, so there is no jobId and nothing to overwrite.
            todo.append((None, url, posting))
            continue
        rid += 1
        try:
            job_id, scored, _ = lookup(token, url, rid)
        except RuntimeError as e:
            print(f"  ! lookup failed ({e}): {posting['company']} — {posting['jobTitle']}")
            continue
        if not job_id:
            continue                       # not in JobSync; discovery will push it
        if scored and not a.force:
            # Already carries a match this pipeline did not create — an assessment
            # made by hand in JobSync. Recorded so the dashboard counts it as
            # assessed rather than awaiting, and so it is visible which records
            # are the owner's own work and must never be overwritten.
            external[url] = datetime.now(timezone.utc).date().isoformat()
            continue                       # never overwrite without --force
        todo.append((job_id, url, posting))

    save_external(external)
    if external:
        print(f"# {len(external)} job(s) already carry a match in JobSync — left untouched")
    print(f"# to score: {len(todo)}")
    if a.dry_run:
        for job_id, url, p in todo:
            print(f"    would score: {p['company']} — {p['jobTitle']}  ({job_id[:8]}…)")
        return 0

    key = S.OPENAI_API_KEY
    if not key:
        print("OPENAI_API_KEY is not set — see .env.example", file=sys.stderr)
        return 2
    results, to_save = [], []
    for job_id, url, p in todo:
        if spend["usd"] >= cfg["max_usd_per_day"]:
            print(f"  ! daily spend cap ${cfg['max_usd_per_day']:.2f} reached — stopping")
            break
        user = (f"PROFILE\n=======\n{profile}\n\n"
                f"POSTING\n=======\n"
                f"Title: {p['jobTitle']}\nCompany: {p['company']}\n"
                f"Location: {p.get('location') or 'not stated'}\n"
                f"Workplace type: {p.get('workplaceType') or 'not stated'}\n"
                f"Employment type: {p.get('jobType') or 'not stated'}\n"
                f"URL: {url}\n\n{(p.get('description') or '')[:cfg['description_chars']]}")
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "local_date": today_local(), "jobId": job_id, "url": url,
               "company": p["company"], "jobTitle": p["jobTitle"],
               "model": cfg["model"], "prompt_version": cfg["prompt_version"]}
        try:
            text, usage = openai_call(key, cfg["model"], prompt, user,
                                      cfg["timeout_seconds"], cfg["max_tokens"],
                                      cfg["retries"], cfg["retry_backoff_seconds"])
        except RuntimeError as e:
            rec["error"] = str(e)[:300]
            log_assessment(rec)
            results.append({**p, "url": url, "error": rec["error"]})
            print(f"  ! {p['company']} — {p['jobTitle']}: {rec['error'][:90]}")
            continue

        spend["calls"] += 1
        spend["usd"] = round(spend["usd"] + cost_of(usage, cfg), 6)
        save_spend(spend)

        m = SCORES_RE.search(text)
        if not m:
            rec["error"] = "model output missing the SCORES line"
            log_assessment(rec)
            results.append({**p, "url": url, "error": rec["error"]})
            print(f"  ! {p['company']} — {p['jobTitle']}: no SCORES line, not saved")
            continue

        model_score, model_rec = int(m.group(1)), m.group(2).lower()
        comps, comp_err = parse_competencies(text)
        if comp_err:
            rec["error"] = f"validation: {comp_err}"
            rec["matchText"] = text.strip()
            log_assessment(rec)
            results.append({**p, "url": url, "error": rec["error"]})
            print(f"  ! {p['company']} — {p['jobTitle']}: {comp_err}, not saved")
            continue

        elig = parse_eligibility(text)
        pref = PREF_RE.search(text)
        verdict_m = VERDICT_RE.search(text)
        score, recommendation, note = validate(model_score, model_rec, comps, elig,
                                               p.get("jobTitle", ""))
        if note:
            # Rewrite the SCORES line so JobSync stores the validated figure, and
            # keep the downgrade visible in the body — a silent correction would
            # be worse than no correction.
            text = SCORES_RE.sub(
                f"SCORES: match={score} recommendation={recommendation}", text, count=1)
            text = text.rstrip() + "\n\n---\n\n" + note + "\n"
            print(f"      downgraded {model_rec}/{model_score} -> {recommendation}/{score}")
            if recommendation == "weak" and verdict_m and verdict_m.group(1).lower() != "skip":
                text = VERDICT_RE.sub("VERDICT: skip", text, count=1)

        rec.update({"model_score": model_score, "model_recommendation": model_rec,
                    "downgraded": bool(note),
                    "competencies": comps,
                    "eligibility": elig,
                    "desirability": pref.group(1).lower() if pref else None,
                    "direction": pref.group(2).lower() if pref else None,
                    "verdict": verdict_m.group(1).lower() if verdict_m else None,
                    "score": score, "recommendation": recommendation,
                    "input_tokens": usage.get("prompt_tokens"),
                    "output_tokens": usage.get("completion_tokens"),
                    "usd": cost_of(usage, cfg),
                    # The full analysis is logged with the metadata. A formatting
                    # bug downstream cost five paid assessments once; output that
                    # has been paid for is written down before anything else runs.
                    "matchText": text.strip()})
        log_assessment(rec)
        results.append({**p, "url": url, "score": score,
                        "recommendation": recommendation,
                        "desirability": pref.group(1).lower() if pref else None,
                        "direction": pref.group(2).lower() if pref else None,
                        "verdict": verdict_m.group(1).lower() if verdict_m else None,
                        "body": SCORES_RE.sub("", text).strip()})
        if job_id:
            to_save.append({"jobId": job_id, "matchText": text.strip()})
        # Flush every batch rather than only at the end. An interruption used to
        # leave analyses scored-but-unsaved: durable in assessments.jsonl, but
        # invisible to find_job, so the next run would pay to score them again.
        if len(to_save) >= 10 and not (a.no_save or a.calibrate):
            try:
                out = mcp(token, "save_match_results_batch", {"results": to_save[:10]}, 4000)
                print(f"# saved {len(to_save[:10])} to JobSync: {out[:100]}")
                del to_save[:10]
            except RuntimeError as e:
                print(f"# ERROR saving batch: {e}", file=sys.stderr)
        vd = verdict_m.group(1).upper() if verdict_m else "NO-VERDICT"
        extra = (f"  {vd:7} [want:{pref.group(1).lower()} dir:{pref.group(2).lower()}]"
                 if pref else f"  {vd:7} [preference line missing]")
        print(f"  {score:3d} {recommendation:8}{extra} {p['company']} — {p['jobTitle']}")

    if to_save and not (a.no_save or a.calibrate):
        for i in range(0, len(to_save), 10):
            chunk = to_save[i:i + 10]
            try:
                out = mcp(token, "save_match_results_batch", {"results": chunk}, 3000 + i)
                print(f"# saved {len(chunk)} to JobSync: {out[:120]}")
            except RuntimeError as e:
                print(f"# ERROR saving batch: {e}", file=sys.stderr)

    try:
        digest = write_digest(
            os.path.join(cfg["digest_dir"], f"digest-{today_local()}.md"), results, cfg, spend)
        print(f"# digest: {digest}")
    except Exception as e:                      # noqa: BLE001 - never lose paid work to formatting
        print(f"# ERROR writing the digest: {type(e).__name__}: {e}", file=sys.stderr)
        print(f"# the assessments are safe in {ASSESS_LOG}", file=sys.stderr)
    print(f"# spend today: ${spend['usd']:.4f} over {spend['calls']} call(s)")
    return 1 if any(r.get("error") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
