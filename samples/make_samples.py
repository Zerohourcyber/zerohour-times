#!/usr/bin/env python3
"""Generate the bundled demo data.

Everything here is FICTIONAL — an invented candidate, invented employers,
invented postings. No real assessment, résumé or job history from any user is
included in this repository. Re-run to regenerate:  python3 samples/make_samples.py
"""
import json, pathlib
from datetime import datetime, timedelta, timezone

OUT = pathlib.Path(__file__).parent / "state"
OUT.mkdir(parents=True, exist_ok=True)
now = datetime.now(timezone.utc)
today = now.date().isoformat()


def body(verdict, elig, comps, readiness, transfer, pref, career, comp, workload, gaps, rec):
    rows = "\n".join(
        f"| {i} | {c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} |"
        for i, c in enumerate(comps, 1))
    eligrows = "\n".join(f"| {e[0]} | {e[1]} | {e[2]} |" for e in elig)
    return f"""## Eligibility

| Requirement | Stated As | Status |
|---|---|---|
{eligrows}

## Core Competencies

| # | Competency | Defining | Critical | Foundational or Learnable | Status | Evidence |
|---|---|---|---|---|---|---|
{rows}

## Qualification — can they do this today

{readiness}

## Transferable Experience

{transfer}

## Preference Fit — would they want this daily

{pref}

## Career Direction

{career}

## Compensation

{comp}

## Workload Indicators

{workload}

## Gaps / Risks

{gaps}

## Recommendation

{rec}
"""


JOBS = [
    dict(co="Northwind Analytics", title="Senior Technical Program Manager, Trust & Safety",
         url="https://example.com/northwind/tpm-trust-safety", loc="Remote — US",
         wp="Remote", jt="Full-time", src="Greenhouse", score=88, rec="strong",
         verdict="apply", want="high", dirn="advances", down=False,
         elig=[("Work authorisation", '"must be authorised to work in the US"', "Met"),
               ("Location", '"Remote — United States"', "Met")],
         comps=[("Cross-functional program delivery in a matrixed org", "yes", "yes",
                 "Foundational", "Demonstrated",
                 "PROFILE: ran governance adopted across 9 organisations, none reporting to them"),
                ("Trust & safety policy and escalation design", "no", "yes", "Foundational",
                 "Transferable", "PROFILE: wrote approval conditions and escalation paths; the "
                 "domain is adjacent, the mechanics are the same"),
                ("Metrics instrumentation for abuse reporting", "no", "no", "Learnable",
                 "Not Documented", "no evidence either way in PROFILE")],
         readiness="Yes. The defining competency — running a programme across teams that do not "
                   "report to you — is demonstrated directly, at larger scale than this posting "
                   "describes.",
         transfer="Escalation and approval design carries over from governance work; the subject "
                  "matter differs, the structure does not.",
         pref="The posting describes coordination, policy and reporting rather than building. That "
              "matches the stated preference to avoid daily software development.",
         career="Advances toward the stated target of technical program management.",
         comp='Posting states a base range of "$140,000 – $175,000". No bonus or equity figure '
              "is given; treat total compensation as not stated.",
         workload='"Partners with on-call engineering during incidents" — quoted. No rotation, '
                  "travel percentage or headcount is stated.",
         gaps="### Confirmed Gaps\n\nNone.\n\n### Not Documented\n\n- Abuse-reporting metrics "
              "tooling.\n\n### Questions for Recruiter\n\n- Is the TPM ever on the incident "
              "rotation, or only partnering with it?\n- What does the escalation path look like "
              "when policy and engineering disagree?",
         rectext="Apply. The core of the role is evidenced, the constraints are respected, and the "
             "single undocumented item is learnable and non-critical."),
    dict(co="Halden Instruments", title="Program Manager, Channel Partnerships",
         url="https://example.com/halden/pm-channel", loc="Remote — US", wp="Remote",
         jt="Full-time", src="Ashby", score=54, rec="partial", verdict="explore",
         want="low", dirn="lateral", down=True,
         elig=[("Work authorisation", '"US-based applicants"', "Met")],
         comps=[("Partner and channel programme management", "yes", "yes", "Foundational",
                 "Not Documented",
                 'POSTING: "own the partner lifecycle end to end" — PROFILE shows no partner or '
                 "channel programme work"),
                ("Programme management across concurrent workstreams", "no", "yes",
                 "Foundational", "Demonstrated", "PROFILE: coordinated 13 concurrent programmes"),
                ("PRM tooling (Allbound, PartnerStack)", "no", "no", "Learnable",
                 "Not Documented", "not evidenced")],
         readiness="Not today. The job exists to run a partner channel, and that specific "
                   "experience is absent — the candidate would be learning the central skill in post.",
         transfer="General programme management is demonstrated and transfers, but it is not the "
                  "same as having run a partner ecosystem.",
         pref="Relationship-led and quota-adjacent work, which sits outside the stated preference.",
         career="Lateral: it uses existing programme skills in a direction away from the stated targets.",
         comp='Posting gives "$120,000 – $185,000 OTE". That is on-target earnings including '
              "commission; **base is not stated** and must be asked about.",
         workload='"Occasional travel to partner events" — quoted; frequency not stated.',
         gaps="### Confirmed Gaps\n\nNone.\n\n### Not Documented\n\n- Partner/channel programme "
              "ownership (defining competency).\n- PRM tooling.\n\n### Questions for Recruiter\n\n"
              "- What is the base salary, separate from OTE?\n- Is partner experience a hard "
              "requirement or a preference?",
         rectext="Explore. Worth a conversation to establish the base salary and how firmly partner "
             "experience is required, but do not treat this as a strong fit."),
    dict(co="Calder & Roe", title="Staff Software Engineer, Platform",
         url="https://example.com/calder/staff-swe", loc="Remote — US", wp="Remote",
         jt="Full-time", src="Lever", score=31, rec="weak", verdict="skip",
         want="low", dirn="diverges", down=False,
         elig=[("Work authorisation", '"US remote"', "Met")],
         comps=[("Designing and shipping production services daily", "yes", "yes",
                 "Foundational", "Confirmed Gap",
                 "PROFILE confirmed limit: not seeking a role whose daily work is software development"),
                ("Distributed systems design", "no", "yes", "Foundational", "Not Documented",
                 "not evidenced")],
         readiness="No. The central work is hands-on engineering, which the profile explicitly "
                   "rules out as a constraint rather than a gap.",
         transfer="Technical fluency is documented, but fluency is not the same as building daily.",
         pref="Directly against a stated constraint.",
         career="Diverges from the stated targets.",
         comp='Base range "$180,000 – $230,000" stated.',
         workload='"Participates in a weekly on-call rotation" — quoted.',
         gaps="### Confirmed Gaps\n\n- Daily hands-on development conflicts with a stated limit.\n\n"
              "### Not Documented\n\n- Distributed systems design.\n\n### Questions for Recruiter\n\n"
              "- None; the constraint is dispositive.",
         rectext="Skip. Well compensated and legitimately interesting, but the day-to-day is the thing "
             "this candidate has ruled out."),
]

queue, assess, research = {}, [], []
for i, j in enumerate(JOBS):
    queue[j["url"]] = {
        "jobTitle": j["title"], "company": j["co"], "jobUrl": j["url"],
        "location": j["loc"], "workplaceType": j["wp"], "jobType": j["jt"],
        "source": j["src"],
        "description": f"(sample posting text for {j['title']} at {j['co']})",
    }
    txt = (f"SCORES: match={j['score']} recommendation={j['rec']}\n"
           f"PREFERENCE: desirability={j['want']} direction={j['dirn']}\n"
           f"VERDICT: {j['verdict']}\n\n"
           + body(j["verdict"], j["elig"], j["comps"], j["readiness"], j["transfer"],
                  j["pref"], j["career"], j["comp"], j["workload"], j["gaps"], j["rectext"]))
    if j["down"]:
        txt += ("\n---\n\n**Automated downgrade.** The model returned `good` / 70, but the "
                "DEFINING competency is not documented: Partner and channel programme management. "
                "Capped at `partial` / 54 by the validator, not by the model.\n")
    assess.append({
        "ts": (now - timedelta(minutes=30 + i)).isoformat(timespec="seconds"),
        "local_date": today, "jobId": f"00000000-0000-4000-8000-00000000000{i}",
        "url": j["url"], "company": j["co"], "jobTitle": j["title"],
        "model": "gpt-4.1", "prompt_version": "match-v6",
        "score": j["score"], "recommendation": j["rec"], "verdict": j["verdict"],
        "desirability": j["want"], "direction": j["dirn"], "downgraded": j["down"],
        "input_tokens": 9100 + i * 60, "output_tokens": 980, "usd": 0.0201,
        "matchText": txt,
    })

research.append({
    "ts": (now - timedelta(minutes=10)).isoformat(timespec="seconds"), "local_date": today,
    "url": JOBS[0]["url"], "company": JOBS[0]["co"], "jobTitle": JOBS[0]["title"],
    "model": "gpt-4.1", "usd": 0.0449, "input_tokens": 17600, "output_tokens": 1150,
    "selected_by": {"verdict": "apply", "desirability": "high", "direction": "advances"},
    "research": """**1. Company stage and size**

- Northwind Analytics is a fictional company used for this demo; in a real run this section
  carries sourced facts with URLs, and says "not found" where a claim cannot be sourced
  ([example.com](https://example.com/northwind/about)).

**2. What the function actually does**

- Sample text showing how research goes beyond the posting wording.

**3. Compensation**

- Posting states a base band. Where an aggregator disagrees with the posting, both figures are
  shown with their sources rather than one being silently chosen.

**4. Questions worth asking**

- Sample questions a real run would generate from the posting's own gaps.
""",
})

(OUT / "queue.json").write_text(json.dumps(queue, indent=1))
(OUT / "assessments.jsonl").write_text("".join(json.dumps(a) + "\n" for a in assess))
(OUT / "research.jsonl").write_text("".join(json.dumps(r) + "\n" for r in research))
(OUT / "last-run.json").write_text(json.dumps({
    "ran_at": (now - timedelta(minutes=45)).isoformat(timespec="seconds"),
    "companies": 119, "fetched": 12548, "kept": len(JOBS), "created": len(JOBS),
    "skipped": 0, "mcp_calls": 7, "rate_limited": False,
    "fetch_errors": [], "push_errors": [], "ok": True}, indent=2))
(OUT / "spend.json").write_text(json.dumps(
    {"date": today, "calls": len(JOBS) + 1, "usd": 0.1052}, indent=2))
print(f"wrote {len(JOBS)} sample jobs to {OUT}")
