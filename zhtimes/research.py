#!/usr/bin/env python3
"""Research the day's most promising postings with one web-grounded call each.

Deliberately NOT an agent. A stateless call per posting, with exactly one tool
(web_search) and no credentials beyond the OpenAI key. Everything it returns is
treated as untrusted text: it is stored and printed, never executed, never used
to select a tool, and never written back into JobSync. Job postings and the web
pages behind them are attacker-controlled input, so the only safe design is one
where a successful prompt injection achieves nothing but a misleading paragraph
in a report a human reads.

Separation of concerns:
  * match.py decides whether the candidate is qualified -> saved to JobSync
  * research.py gathers context about the employer      -> saved HERE only
Research never touches matchScore/matchData, so it cannot overwrite an
assessment, and the two can fail independently.

Shares match.py's $2/day ledger so the two stages cannot jointly overspend.
"""

import argparse, json, os, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import match as M                       # reuse the ledger, paths and TZ — one budget, one clock

RESEARCH_LOG = f"{M.STATE_DIR}/research.jsonl"
OPENAI_RESPONSES = M.S.OPENAI_RESPONSES

PROMPT = """Research this employer and role using web search. Cite every factual claim with a
source URL. Where you cannot source something, write "not found" — never infer, never estimate.
If sources disagree, say so explicitly and give both figures with their sources.

Company: {company}
Role: {title}
Posting URL: {url}

Cover, briefly:
1. Company stage, size, ownership and any material news in the last 6 months.
2. What this function actually does day to day, beyond the posting's wording. Note anything that
   suggests the real work differs from the title.
3. Published compensation data for this role and level in the US. State base separately from OTE,
   bonus or equity. If only an OTE is published, say the base is not established.
4. The qualifications in the posting that are ambiguous — where a candidate could not tell from the
   text whether they qualify — and what would resolve each.
5. Four specific questions worth asking a recruiter about THIS role, each aimed at deciding whether
   it is worth pursuing. No generic questions.

Be concise and factual. Omit anything you cannot source."""


def already_researched(path=RESEARCH_LOG):
    done = set()
    try:
        with open(path) as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["url"])
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError:
        pass
    return done


def append_log(rec, path=RESEARCH_LOG):
    """Append-only, written immediately after the call returns, before any
    formatting runs. Paid output is never held only in memory."""
    try:
        os.makedirs(M.STATE_DIR, exist_ok=True)
        with open(path, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError as e:
        print(f"# WARN could not append research log: {e}", file=sys.stderr)


# Selection weights: qualification evidence and preference alignment, NOT the
# numeric score, which calibration showed is the least stable signal we have.
VERDICT_W = {"apply": 3, "explore": 2, "skip": 0}
WANT_W = {"high": 2, "medium": 1, "low": 0}
DIR_W = {"advances": 2, "lateral": 1, "diverges": 0}


def candidates(day, limit, skip_urls):
    rows = {}
    try:
        with open(M.ASSESS_LOG) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("local_date") != day or r.get("score") is None:
                    continue
                rows[r["url"]] = r          # last assessment per URL wins
    except OSError as e:
        print(f"cannot read {M.ASSESS_LOG}: {e}", file=sys.stderr)
        return []

    scored = []
    for url, r in rows.items():
        if url in skip_urls:
            continue
        if r.get("verdict") == "skip":
            continue                        # never spend research on a skip
        rank = (VERDICT_W.get(r.get("verdict"), 1)
                + WANT_W.get(r.get("desirability"), 0)
                + DIR_W.get(r.get("direction"), 0))
        scored.append((rank, r.get("score") or 0, r))
    scored.sort(key=lambda t: (-t[0], -t[1]))
    return [r for _, _, r in scored[:limit]]


def research(key, posting, model, timeout, max_tokens, retries, backoff):
    body = json.dumps({
        "model": model,
        "tools": [{"type": "web_search"}],      # the ONLY tool this call may use
        "input": PROMPT.format(company=posting["company"], title=posting["jobTitle"],
                               url=posting["url"]),
        "max_output_tokens": max_tokens,
    }).encode()
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(OPENAI_RESPONSES, data=body, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json",
            "User-Agent": M.UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.load(r)
            text = ""
            for item in d.get("output", []):
                for c in item.get("content", []) or []:
                    if c.get("type") == "output_text":
                        text += c["text"]
            return text, d.get("usage", {})
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:200]}"
            if e.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = f"{type(e).__name__}: {e}"
        if attempt < retries:
            time.sleep(backoff * (2 ** attempt))
    raise RuntimeError(last or "research call failed")


def main():
    ap = argparse.ArgumentParser(description="Research today's most promising postings")
    ap.add_argument("--config", default=M.S.CONFIG_PATH)
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--date", help="assessment date to draw from (default: today, Denver)")
    a = ap.parse_args()

    raw = json.load(open(a.config))
    cfg = raw.get("research", {})
    cfg.setdefault("model", "gpt-4.1")
    cfg.setdefault("timeout_seconds", 180)
    cfg.setdefault("max_tokens", 1300)
    cfg.setdefault("retries", 1)
    cfg.setdefault("retry_backoff_seconds", 4)
    mcfg = raw.get("matching", {})
    usd_in = mcfg.get("usd_per_1k_input", 0.002)
    usd_out = mcfg.get("usd_per_1k_output", 0.008)
    cap = mcfg.get("max_usd_per_day", 2.00)

    day = a.date or M.today_local()
    done = already_researched()
    picks = candidates(day, a.limit, done)
    spend = M.load_spend()

    print(f"# {datetime.now(M.TZ).strftime('%Y-%m-%d %H:%M %Z')} | model={cfg['model']} "
          f"| shared budget ${cap - spend['usd']:.2f} left of ${cap:.2f}")
    print(f"# already researched: {len(done)} | selected {len(picks)} "
          f"by verdict + desirability + direction (not by score)")
    for p in picks:
        print(f"    {p['company']} — {p['jobTitle'][:52]}  "
              f"[{p.get('verdict')}/{p.get('desirability')}/{p.get('direction')}, "
              f"score {p.get('score')}]")
    if a.dry_run or not picks:
        return 0

    key = M.S.OPENAI_API_KEY
    if not key:
        print("OPENAI_API_KEY is not set — see .env.example", file=sys.stderr)
        return 2
    total = 0.0
    for p in picks:
        if spend["usd"] >= cap:
            print(f"  ! shared daily cap ${cap:.2f} reached — stopping")
            break
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "local_date": day, "url": p["url"], "company": p["company"],
               "jobTitle": p.get("jobTitle"), "model": cfg["model"],
               "selected_by": {"verdict": p.get("verdict"),
                               "desirability": p.get("desirability"),
                               "direction": p.get("direction")}}
        try:
            text, usage = research(key, p, cfg["model"], cfg["timeout_seconds"],
                                   cfg["max_tokens"], cfg["retries"],
                                   cfg["retry_backoff_seconds"])
        except RuntimeError as e:
            rec["error"] = str(e)[:300]
            append_log(rec)
            print(f"  ! {p['company']}: {rec['error'][:100]}")
            continue
        cost = round(usage.get("input_tokens", 0) / 1000 * usd_in
                     + usage.get("output_tokens", 0) / 1000 * usd_out, 6)
        rec.update({"input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "usd": cost, "research": text})
        append_log(rec)                       # durable before anything else
        spend["usd"] = round(spend["usd"] + cost, 6)
        spend["calls"] += 1
        M.save_spend(spend)
        total += cost
        print(f"  ok  {p['company']} — {p['jobTitle'][:44]}  "
              f"{usage.get('input_tokens')}in/{usage.get('output_tokens')}out  ${cost:.4f}")

    print(f"# research cost this run ${total:.4f}; shared day total ${spend['usd']:.4f}")
    print(f"# appended to {RESEARCH_LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
