#!/usr/bin/env python3
"""Resolve company names to verified ATS board tokens.

Guessing a slug is cheap; guessing wrong is expensive, because an unverified
token fails silently and looks exactly like "this employer has no openings".
So every candidate is probed against the real board API and only kept if it
returns postings.

Usage:
    python3 resolve.py --names names.txt --out resolved.json
    python3 resolve.py --names names.txt --merge config.json
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as S

import argparse, json, re, sys, time, urllib.error, urllib.request

TIMEOUT = 15
UA = S.USER_AGENT
PAUSE = 0.3      # be polite: these are free endpoints run for employers, not us

PROBES = {
    "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/{t}/jobs",
                   lambda d: len(d.get("jobs", []))),
    "lever":      ("https://api.lever.co/v0/postings/{t}?mode=json",
                   lambda d: len(d) if isinstance(d, list) else 0),
    "ashby":      ("https://api.ashbyhq.com/posting-api/job-board/{t}",
                   lambda d: len(d.get("jobs", []))),
}

ALIASES = {
    "weights and biases": ["wandb", "weightsandbiases"],
    "hugging face": ["huggingface"],
    "grafana labs": ["grafanalabs", "grafana"],
    "crowdstrike": ["crowdstrike", "crowdstrikeinc"],
    "doordash": ["doordash", "doordashusa"],
    "1password": ["1password", "agilebits"],
    "e2b": ["e2b"],
}


def slugs(name):
    """Candidate board tokens, most likely first.

    Boards use short lowercase names, but not always the obvious one, so this
    tries the compact form, the hyphenated form, the first word alone, and the
    name with a trailing generic word (Security, Labs, Health, AI...) removed.
    Every candidate is still probed against the live API before it is trusted —
    guessing is cheap, and a wrong token fails silently and looks exactly like
    an employer with no openings.
    """
    base = name.strip().lower()
    out = list(ALIASES.get(base, []))
    base = re.sub(r"[&'.,]", "", base)
    base = re.sub(r"\b(inc|llc|ltd|corp|corporation|co|technologies|technology|the)\b", " ", base)
    base = re.sub(r"\s+", " ", base).strip()

    compact = re.sub(r"[^a-z0-9]", "", base)
    hyphen = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    words = base.split()
    firstword = words[0] if words else ""
    trimmed = ""
    if len(words) > 1 and words[-1] in (
            "security", "labs", "lab", "health", "ai", "software", "systems",
            "cloud", "data", "group", "holdings", "io", "hq"):
        trimmed = "".join(words[:-1])

    for cand in (compact, hyphen, firstword, trimmed):
        if cand and cand not in out:
            out.append(cand)
    return out


def probe(board, token):
    url, count = PROBES[board]
    req = urllib.request.Request(url.format(t=token),
                                 headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if r.status != 200:
                return None
            return count(json.load(r))
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, TimeoutError):
        return None

def resolve(name, boards=("greenhouse", "lever", "ashby")):
    for token in slugs(name):
        for board in boards:
            n = probe(board, token)
            time.sleep(PAUSE)
            if n:                      # 0 openings is not proof of a valid board
                return {"board": board, "token": token, "company": name, "open": n}
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", required=True, help="file with one company name per line")
    ap.add_argument("--out")
    ap.add_argument("--merge", help="merge verified entries into this config.json watchlist")
    a = ap.parse_args()

    names = [l.strip() for l in open(a.names) if l.strip() and not l.startswith("#")]
    found, missing = [], []
    for name in names:
        hit = resolve(name)
        if hit:
            found.append(hit)
            print(f"  OK    {hit['board']:10} {hit['token']:22} {name}  ({hit['open']} open)")
        else:
            missing.append(name)
            print(f"  --    {'':10} {'':22} {name}")

    print(f"\nresolved {len(found)}/{len(names)}; unresolved: {', '.join(missing) or 'none'}")

    if a.out:
        json.dump(found, open(a.out, "w"), indent=2)
        print(f"wrote {a.out}")

    if a.merge:
        cfg = json.load(open(a.merge))
        have = {(e["board"], e["token"]) for e in cfg["watchlist"]}
        added = 0
        for hit in found:
            if (hit["board"], hit["token"]) not in have:
                cfg["watchlist"].append({"board": hit["board"], "token": hit["token"],
                                         "company": hit["company"]})
                added += 1
        cfg["watchlist"].sort(key=lambda e: (e["board"], e["token"]))
        json.dump(cfg, open(a.merge, "w"), indent=2)
        print(f"merged {added} new entries into {a.merge} "
              f"({len(cfg['watchlist'])} total)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
