#!/usr/bin/env python3
"""Score the matcher against the adversarial validation set.

Mechanical checks only. Anything needing judgement (is this Demonstrated claim
actually supported?) is surfaced for human review rather than asserted.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as S

import argparse, collections, json, sys

# What each category SHOULD produce. These are expectations about the floor, not
# ground truth about the roles: a flag means "look at this", not "this is wrong".
EXPECT = {
    "swe_handson":           {"max": "partial", "why": "daily hands-on development is a confirmed limit"},
    "junior":                {"max": "partial", "why": "junior scope against 20 years of experience"},
    "non_remote":            {"max": "partial", "why": "remote-only is a confirmed limit"},
    "mandatory_qual_lacked": {"max": "good",    "why": "a mandatory qualification may be absent"},
    "defining_missing":      {"max": "partial", "why": "the defining competency sits outside the profile"},
    "misleading_title":      {"max": "good",    "why": "title suggests oversight, duties suggest building"},
    "target_match":          {"max": "strong",  "why": "genuine target role"},
    "original_five":         {"max": "strong",  "why": "genuine target role"},
}
ORDER = ["weak", "partial", "good", "strong"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=f"{S.STATE_DIR}/assessments.jsonl")
    ap.add_argument("--queue", default=f"{S.STATE_DIR}/calib-queue.json")
    ap.add_argument("--version", default="match-v5")
    a = ap.parse_args()

    queue = json.load(open(a.queue))
    rows = [json.loads(l) for l in open(a.log)]
    runs = {r["url"]: r for r in rows if r.get("prompt_version") == a.version and r.get("url") in queue}

    print(f"{'CATEGORY':<22} {'QUAL':<13} {'WANT/DIR':<18} {'DEFINING COMPETENCY':<40} ELIG")
    print("-" * 118)
    flags = collections.defaultdict(list)
    by_cat = collections.defaultdict(list)

    for url, p in queue.items():
        cat = p.get("_category", "?")
        r = runs.get(url)
        if not r:
            print(f"{cat:<22} {'(not scored)':<13}")
            continue
        if r.get("error"):
            print(f"{cat:<22} {'ERROR':<13} {r['error'][:70]}")
            flags["errors"].append((cat, p["jobTitle"], r["error"]))
            continue

        rec, sc = r["recommendation"], r["score"]
        defn = next((c for c in r["competencies"] if c.get("defining")), None)
        elig = r.get("eligibility") or []
        notmet = [e for e in elig if e["status"] == "not met"]
        unver = [e for e in elig if e["status"] == "unverifiable"]
        by_cat[cat].append(rec)

        print(f"{cat:<22} {rec+'/'+str(sc):<13} "
              f"{str(r.get('desirability'))+'/'+str(r.get('direction')):<18} "
              f"{(defn['competency'][:37] + ' [' + defn['status'][:4] + ']') if defn else '(none marked)':<40} "
              f"{'NOT MET:' + notmet[0]['requirement'][:26] if notmet else ('unver:' + str(len(unver)) if unver else 'ok')}")

        exp = EXPECT.get(cat)
        if exp and ORDER.index(rec) > ORDER.index(exp["max"]):
            flags["above_expected"].append((cat, p["company"], p["jobTitle"], f"{rec}/{sc}", exp["why"]))
        if rec == "strong" and cat not in ("target_match", "original_five"):
            flags["false_strong"].append((cat, p["company"], p["jobTitle"], f"{rec}/{sc}"))
        if notmet and cat in ("target_match", "original_five"):
            flags["suspect_skip"].append((cat, p["company"], p["jobTitle"], notmet[0]["requirement"]))
        if not defn:
            flags["no_defining"].append((cat, p["company"], p["jobTitle"]))
        if r.get("downgraded"):
            flags["validator_intervened"].append((cat, p["company"], p["jobTitle"],
                                                  f"{r['model_recommendation']}/{r['model_score']} -> {rec}/{sc}"))

    print("\n=== distribution by category ===")
    for cat, recs in sorted(by_cat.items()):
        print(f"  {cat:<22} {collections.Counter(recs).most_common()}")

    print("\n=== flags for review ===")
    for name, items in flags.items():
        print(f"\n  {name} ({len(items)}):")
        for it in items:
            print("    " + " | ".join(str(x)[:60] for x in it))

    scored = [r for r in runs.values() if not r.get("error")]
    usd = sum(r.get("usd") or 0 for r in scored)
    print(f"\n=== totals ===\n  scored {len(scored)}/{len(queue)}  cost ${usd:.3f}  "
          f"validator interventions {len(flags['validator_intervened'])}  "
          f"false strong {len(flags['false_strong'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
