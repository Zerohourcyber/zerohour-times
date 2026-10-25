#!/usr/bin/env python3
"""Build a deliberately adversarial validation set for the matcher.

Tuning against five promising roles only tests the ceiling. This samples the
floor too: engineering roles, junior roles, non-remote roles, misleading titles,
and roles with mandatory qualifications the candidate does not hold. Output is a
queue file for `match.py --calibrate`, which never touches JobSync.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as S

import argparse, json, re, sys
import discover as d

CATEGORIES = {
    "swe_handson": (
        lambda t, x, p: re.search(
            r"\b(software|backend|back-end|frontend|front-end|full[ -]stack|infrastructure|"
            r"platform|systems|security|ml|machine learning|data)\s+engineer\b", t)
        or re.search(r"\b(developer|programmer|sre|site reliability)\b", t)),
    "junior": (
        lambda t, x, p: re.search(r"\b(associate|junior|jr\.?|intern|entry[- ]level|new grad|"
                                  r"apprentice|graduate)\b", t) or re.search(r"\s(i|ii)$", t)),
    "non_remote": (
        lambda t, x, p: p.get("workplaceType") in ("Onsite", "Hybrid")),
    "misleading_title": (
        lambda t, x, p: ("program manager" in t or "programme manager" in t)
        and re.search(r"\b(write code|writing code|coding|hands-on engineering|"
                      r"software development life ?cycle|programming language|"
                      r"debug|pull request)\b", x)),
    "mandatory_qual_lacked": (
        lambda t, x, p: re.search(
            r"\b(pmp|cissp|cisa|cism|crisc|juris doctor|\bjd\b|ph\.?d|m\.?d\.?|"
            r"active (ts/sci|top secret|secret) clearance|registered nurse|\bcpa\b)\b", x)
        or re.search(r"\b1[5-9]\+?\s*years\b", x)),
    "defining_missing": (
        lambda t, x, p: re.search(r"\b(partner|channel|alliance|sales|revenue|marketing|"
                                  r"procurement|supply chain|m&a|mergers)\b", t)
        and re.search(r"\b(manager|lead|director|program)\b", t)),
    "target_match": (
        lambda t, x, p: re.search(r"\b(technical program manager|program manager|governance|"
                                  r"grc|compliance|risk)\b", t)
        and p.get("workplaceType") == "Remote"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=S.CONFIG_PATH)
    ap.add_argument("--out", default="calib-queue.json")
    ap.add_argument("--per-category", type=int, default=3)
    ap.add_argument("--include", default="", help="comma-separated URLs to force-include")
    a = ap.parse_args()

    cfg = json.load(open(a.config))
    buckets = {k: [] for k in CATEGORIES}
    seen = set()
    fetched = 0

    for entry in cfg["watchlist"]:
        try:
            raw = list(d.BOARDS[entry["board"]](entry["token"]))
        except Exception as e:                       # noqa: BLE001 - a dead board must not stop the sweep
            print(f"  ! {entry['board']}/{entry['token']}: {e}", file=sys.stderr)
            continue
        fetched += len(raw)
        for r in raw:
            desc = d.strip_html(r.get("description"))
            posting = {
                "jobTitle": d.canonical_title(r.get("title")),
                "company": d.canonical_company(entry.get("company") or entry["token"]),
                "jobUrl": d.normalize_url(r.get("url")),
                "location": (r.get("location") or "").strip() or None,
                "workplaceType": d.workplace_type(r.get("workplace"), r.get("location"), desc),
                "jobType": d.job_type(r.get("commitment")),
                "description": desc,
                "source": entry["board"].capitalize(),
            }
            if not (posting["jobTitle"] and posting["company"] and posting["jobUrl"]):
                continue
            if posting["jobUrl"] in seen:
                continue
            t = posting["jobTitle"].lower()
            x = (desc or "").lower()
            for name, test in CATEGORIES.items():
                if len(buckets[name]) >= a.per_category:
                    continue
                try:
                    hit = test(t, x, posting)
                except Exception:                    # noqa: BLE001
                    hit = False
                if hit:
                    posting["_category"] = name
                    buckets[name].append(posting)
                    seen.add(posting["jobUrl"])
                    break

    out = {}
    for name, items in buckets.items():
        for p in items:
            out[p["jobUrl"]] = p
        print(f"  {name:24} {len(items)}")
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"\nfetched {fetched} postings; wrote {len(out)} to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
