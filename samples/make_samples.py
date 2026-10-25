#!/usr/bin/env python3
"""Generate the bundled demo data.

Everything here is FICTIONAL — an invented candidate, invented employers,
invented postings, invented sources. No real assessment, resume or job history
from any user is included in this repository. Every URL points at example.com,
which exists precisely so documentation can cite something that is obviously not
a real source.

The depth matters. This data is what a stranger sees in demo mode before they
install anything, and a thin sample makes the tool look thin — so these
assessments carry the same sections, the same evidence discipline and roughly
the same length as a real run produces.

Re-run to regenerate:  python3 samples/make_samples.py
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
         elig=[("US work authorisation", '"Must be authorised to work in the United States '
                'without sponsorship"', "Met"),
               ("Remote work", '"Workplace type: Remote"', "Met"),
               ("7+ years in technical program management or an adjacent discipline",
                '"You have 7+ years running technical programmes, or equivalent experience '
                'in a related field."', "Met"),
               ("Bachelor's degree or equivalent practical experience",
                '"Bachelor\'s degree, or equivalent practical experience."', "Met")],
         comps=[("Cross-functional programme delivery in a matrixed organisation", "yes", "yes",
                 "Foundational", "Demonstrated",
                 'POSTING: "drive programmes across Policy, Engineering and Legal, none of whom '
                 'report to you". PROFILE: "built and ran a governance programme adopted across '
                 '9 organisations, none of which reported to me" [R]'),
                ("Policy and escalation design under time pressure", "yes", "yes",
                 "Foundational", "Demonstrated",
                 'POSTING: "define escalation paths and the conditions that trigger them". '
                 'PROFILE: "designed where automation acted and where a person still had to: '
                 'review checkpoints and written approval conditions" [R]'),
                ("Incident and escalation reporting to non-technical audiences", "no", "yes",
                 "Foundational", "Demonstrated",
                 'POSTING: "brief leadership weekly". PROFILE: "reported programme status to '
                 'executive and non-technical audiences on a weekly cadence" [R]'),
                ("Trust & safety domain experience specifically", "no", "yes", "Foundational",
                 "Transferable",
                 "PROFILE evidences governance, risk and approval-path design; the mechanics are "
                 "the same and the subject matter differs. Adjacent, not identical"),
                ("Abuse-reporting metrics instrumentation", "no", "no", "Learnable",
                 "Not Documented",
                 "no evidence either way in PROFILE — absence of evidence, recorded as such"),
                ("SQL or equivalent for self-serve analysis", "no", "no", "Learnable",
                 "Not Documented", 'POSTING lists it as "nice to have"; PROFILE does not '
                 "evidence it")],
         readiness="Yes. The defining competency — running a programme across teams that do not "
                   "report to you — is directly demonstrated, at a larger scale than this posting "
                   "describes (9 organisations against the 3 functions named here). Escalation "
                   "and approval design, the second defining competency, is evidenced in the "
                   "candidate's own words. Both critical reporting competencies are demonstrated. "
                   "Nothing central to the role depends on a transfer of experience.",
         transfer="One critical competency requires transfer: trust & safety as a domain. The "
                  "candidate has not worked in trust & safety, and this assessment does not treat "
                  "governance experience as equivalent to it. What does carry over is structural "
                  "— escalation paths, written approval conditions, and the discipline of "
                  "deciding in advance who may act and when. The posting describes the role in "
                  "those structural terms rather than in content-moderation terms, which is why "
                  "this is scored as transferable rather than as a gap.",
         pref="- The role is fully remote, matching the candidate's stated constraint.\n"
              "- The work described is coordination, policy design and reporting — not daily "
              "software development, which the profile records as a confirmed limit.\n"
              "- The posting names no on-call rotation for this role, only partnership with one.",
         career="- Directly on the candidate's stated target of technical programme management.\n"
                "- Trust & safety adds a governance domain adjacent to the stated interest in "
                "risk and policy work, which widens rather than narrows the next step.",
         comp='- Base salary: "$140,000 — $175,000 USD" (stated in the posting).\n'
              "- Equity: not mentioned. Bonus: not mentioned. Treat total compensation as "
              "**not stated** rather than assuming base is the whole package.\n"
              "- The stated base band meets the candidate's recorded target of $135,000 – "
              "$165,000 at the midpoint and exceeds it at the top.",
         workload='- Reporting line: "reports to the Director of Trust & Safety Operations" '
                  "— quoted.\n"
                  '- On-call: "partners with on-call engineering during incidents" — quoted. '
                  "The role itself is not placed on a rotation in the posting text.\n"
                  "- Headcount, team size and programme count: not stated.\n"
                  "- Travel: not stated.\n"
                  '- Hours language: "occasional evening coverage during a major incident" '
                  "— quoted; frequency not defined.\n"
                  '- Boilerplate present ("fast-paced", "wear many hats") but no concrete '
                  "workload indicator attached to it.",
         gaps="### Confirmed Gaps\n\n"
              "- None. Nothing the posting requires is contradicted by a recorded limit.\n\n"
              "### Not Documented\n\n"
              "- Abuse-reporting metrics tooling (not a stated requirement).\n"
              "- SQL for self-serve analysis (listed as nice-to-have).\n"
              "- Trust & safety as a named domain, as distinct from the governance work that is "
              "evidenced.\n\n"
              "### Questions for Recruiter\n\n"
              "- Is this TPM ever placed on the incident rotation, or only partnering with it?\n"
              "- What happens when Policy and Engineering disagree — who holds the decision?\n"
              "- Is equity part of the package, and is the base band national or location-adjusted?",
         rectext="Apply. Both defining competencies are demonstrated rather than inferred, the "
                 "role respects the candidate's stated constraint on daily development work, and "
                 "the compensation band covers the recorded target. The single domain gap is "
                 "adjacent and is named here rather than papered over."),

    dict(co="Vance Maritime Group", title="Director, Security Governance & Compliance",
         url="https://example.com/vance/dir-security-governance", loc="Remote — US",
         wp="Remote", jt="Full-time", src="Greenhouse", score=81, rec="strong",
         verdict="apply", want="high", dirn="advances", down=False,
         elig=[("US work authorisation", '"US-based, no sponsorship available"', "Met"),
               ("Remote work", '"Remote (United States)"', "Met"),
               ("8+ years in security governance, risk or compliance",
                '"8+ years in security GRC or a closely related field."', "Met"),
               ("Audit experience against a recognised framework",
                '"Demonstrated experience delivering SOC 2, ISO 27001 or equivalent audits."',
                "Met")],
         comps=[("Security governance programme ownership", "yes", "yes", "Foundational",
                 "Demonstrated",
                 'POSTING: "own the governance programme end to end". PROFILE: "built and ran a '
                 'governance programme adopted across 9 organisations" [R]'),
                ("Audit delivery against a recognised framework", "yes", "yes", "Foundational",
                 "Demonstrated",
                 'POSTING: "lead SOC 2 Type II and ISO 27001 cycles". PROFILE: "delivered audit '
                 'evidence packages and control narratives across two annual cycles" [R]'),
                ("Control design and policy authoring", "no", "yes", "Foundational",
                 "Demonstrated",
                 'PROFILE: "wrote control narratives, approval conditions and the policy set '
                 'they sat under" [R]'),
                ("Managing a team of analysts", "no", "yes", "Foundational", "Transferable",
                 'POSTING: "lead a team of three". PROFILE evidences leading programmes and '
                 "coordinating contributors, but does not state direct line management [R]"),
                ("Commercial GRC tooling (Vanta, Drata, LogicGate)", "no", "no", "Learnable",
                 "Not Documented",
                 'POSTING lists this as "familiarity preferred"; PROFILE does not evidence a '
                 "named platform"),
                ("Third-party and vendor risk assessment", "no", "no", "Learnable",
                 "Not Documented", "not evidenced in PROFILE either way")],
         readiness="Yes, for the governance and audit core. Both defining competencies — owning "
                   "the programme and delivering audits against a recognised framework — are "
                   "directly evidenced, including the unglamorous part, which is control "
                   "narratives and evidence packages rather than strategy decks. The one "
                   "reservation is people management: the posting states a team of three, and "
                   "the profile does not record direct reports.",
         transfer="Line management is the transfer. The candidate has led programmes and "
                  "coordinated contributors across organisations without authority over them, "
                  "which is in some respects harder, but it is not the same as holding "
                  "performance conversations and managing a headcount. This assessment does not "
                  "treat the two as equivalent, and the question below exists to resolve it.",
         pref="- Fully remote, matching the stated constraint.\n"
              "- The daily work is governance, audit and policy — squarely inside the stated "
              "preference and away from hands-on development.\n"
              "- Director scope implies more stakeholder management than individual delivery, "
              "which the profile's evidence supports.",
         career="- Advances the stated target of security GRC, and does so at a title step up.\n"
                "- Adds formal people leadership, which the record does not currently show and "
                "which most further steps in this direction will require.",
         comp='- Base salary: "$165,000 — $200,000 USD" (stated).\n'
              '- Equity: "participation in the company equity plan" — no size or structure given, '
              "so the value is **not stated**.\n"
              "- The base band exceeds the candidate's recorded target of $135,000 – $165,000 "
              "across its whole range.",
         workload="- Reporting line: \"reports to the VP, Security\" — quoted.\n"
                  '- Team: "a team of three analysts" — quoted. This is the clearest workload '
                  "signal in the posting.\n"
                  '- Audit cadence: "two external audit cycles per year" — quoted.\n'
                  "- On-call: not mentioned.\n"
                  '- Travel: "up to 10% for audit fieldwork" — quoted.\n'
                  "- No language about after-hours expectations either way.",
         gaps="### Confirmed Gaps\n\n"
              "- None.\n\n"
              "### Not Documented\n\n"
              "- Direct line management of a team (the posting states three reports).\n"
              "- A named commercial GRC platform.\n"
              "- Third-party/vendor risk assessment as a distinct function.\n\n"
              "### Questions for Recruiter\n\n"
              "- Is prior direct people management a hard requirement, or is programme leadership "
              "accepted in its place?\n"
              "- Which GRC platform is in use, and is the team migrating or settled?\n"
              "- Does the 10% travel figure include the audit fieldwork weeks, or sit on top "
              "of them?",
         rectext="Apply. The governance and audit core is demonstrated in detail, compensation "
                 "clears the recorded target outright, and the role advances the stated "
                 "direction. The people-management question is real and is worth raising early "
                 "rather than discovering in a final round."),

    dict(co="Halden Instruments", title="Program Manager, Channel Partnerships",
         url="https://example.com/halden/pm-channel", loc="Remote — US", wp="Remote",
         jt="Full-time", src="Ashby", score=54, rec="partial", verdict="explore",
         want="low", dirn="lateral", down=True,
         elig=[("US work authorisation", '"US-based applicants only"', "Met"),
               ("Remote work", '"Remote, with occasional travel"', "Met"),
               ("5+ years in partner, channel or alliance programmes",
                '"5+ years running partner or channel programmes."', "Not Met"),
               ("Bachelor's degree", '"Bachelor\'s degree required."', "Met")],
         comps=[("Partner and channel programme ownership", "yes", "yes", "Foundational",
                 "Not Documented",
                 'POSTING: "own the partner lifecycle end to end, from recruitment through '
                 'co-sell". PROFILE shows no partner, channel or alliance programme work of any '
                 "kind"),
                ("Programme management across concurrent workstreams", "no", "yes",
                 "Foundational", "Demonstrated",
                 'PROFILE: "coordinated 13 concurrent programmes against a shared delivery '
                 'calendar" [R]'),
                ("Commercial negotiation with external parties", "no", "yes", "Foundational",
                 "Transferable",
                 "PROFILE evidences negotiating treatment plans and control exceptions with "
                 "internal owners; external commercial negotiation is not evidenced [R]"),
                ("PRM tooling (Allbound, PartnerStack, Impartner)", "no", "no", "Learnable",
                 "Not Documented", "not evidenced"),
                ("Quota or revenue-carrying experience", "no", "no", "Foundational",
                 "Not Documented",
                 'POSTING: "partners with Sales against a shared number" — PROFILE evidences no '
                 "revenue responsibility")],
         readiness="Not today. The job exists to run a partner channel, and that specific "
                   "experience is absent from the record. The candidate would be learning the "
                   "central skill of the role in post, against a shared revenue number, which is "
                   "a materially different proposition from learning a tool or a domain.",
         transfer="Programme management transfers cleanly and is demonstrated at scale. What does "
                  "not transfer is the partner relationship itself: recruiting, enabling and "
                  "holding commercial partners to a number is its own discipline, and the record "
                  "contains nothing that stands in for it. Treating general programme skill as a "
                  "substitute here would be exactly the inference this system is built to refuse.",
         pref="- Relationship-led and quota-adjacent work, which sits outside the stated "
              "preference for governance and delivery work.\n"
              '- "Occasional travel to partner events" against a stated preference for remote '
              "work without regular travel.\n"
              "- The posting's own framing is revenue-first, which does not match the profile's "
              "stated interests.",
         career="- Lateral: it uses existing programme skills in a direction away from the "
                "stated targets of technical programme management and security GRC.\n"
                "- Partner programme experience is a genuine specialism, but it is not one the "
                "candidate has said they want.",
         comp='- "$120,000 — $185,000 OTE" (stated). OTE is on-target earnings **including '
              "commission**.\n"
              "- **Base is not stated.** The low end of base could sit well under the "
              "candidate's recorded target of $135,000 – $165,000 once commission is stripped "
              "out, and this cannot be resolved from the posting.\n"
              "- No equity mentioned.",
         workload='- Reporting line: "reports to the Senior Director, Partnerships" — quoted.\n'
                  '- Travel: "occasional travel to partner events" — quoted; frequency not '
                  "stated.\n"
                  '- Number: "partners with Sales against a shared number" — quoted. The role '
                  "carries revenue expectations even if it does not carry a personal quota.\n"
                  "- Partner count, team size and on-call: not stated.",
         gaps="### Confirmed Gaps\n\n"
              "- None. The absence of partner experience is undocumented, not contradicted — "
              "the candidate has never said they would not do this work.\n\n"
              "### Not Documented\n\n"
              "- Partner/channel programme ownership — the **defining** competency.\n"
              "- Quota or revenue responsibility.\n"
              "- PRM tooling.\n\n"
              "### Questions for Recruiter\n\n"
              "- What is the base salary, separate from OTE?\n"
              "- Is partner programme experience a hard requirement or a strong preference?\n"
              "- What does the shared number mean in practice for this role's review?",
         rectext="Explore. Worth one conversation to establish the base salary and how firmly "
                 "partner experience is required, because the OTE framing hides the only number "
                 "that matters here. Do not treat this as a strong fit: the competency the job "
                 "is built around is the one the record does not evidence."),

    dict(co="Calder & Roe", title="Staff Software Engineer, Platform",
         url="https://example.com/calder/staff-swe", loc="Remote — US", wp="Remote",
         jt="Full-time", src="Lever", score=31, rec="weak", verdict="skip",
         want="low", dirn="diverges", down=False,
         elig=[("US work authorisation", '"US remote"', "Met"),
               ("Remote work", '"Remote — United States"', "Met"),
               ("8+ years building production software",
                '"8+ years shipping production services."', "Not Met")],
         comps=[("Designing and shipping production services daily", "yes", "yes",
                 "Foundational", "Confirmed Gap",
                 "PROFILE confirmed limit: \"not seeking a role whose daily work is software "
                 'development" [O]. This is a stated constraint, not missing evidence'),
                ("Distributed systems design", "no", "yes", "Foundational", "Not Documented",
                 "not evidenced in PROFILE"),
                ("Production on-call ownership", "no", "yes", "Foundational", "Not Documented",
                 'POSTING: "participates in a weekly on-call rotation" — not evidenced'),
                ("Technical fluency with engineering teams", "no", "no", "Foundational",
                 "Demonstrated",
                 'PROFILE: "ran programmes with engineering teams and translated between them '
                 'and non-technical stakeholders" [R]')],
         readiness="No. The central work is hands-on engineering, which the profile explicitly "
                   "rules out. This is recorded as a confirmed gap rather than an undocumented "
                   "one, and the distinction is the whole point: the candidate has not failed to "
                   "evidence this, they have stated they do not want it.",
         transfer="Technical fluency is documented and genuine — this candidate works with "
                  "engineers and is credible with them. Fluency is not the same as building "
                  "daily, and no amount of adjacent credibility closes that distance for a Staff "
                  "engineering role.",
         pref="- Directly against a stated constraint, which is the strongest negative signal "
              "this system records.\n"
              '- "Weekly on-call rotation" against a stated preference for predictable hours.',
         career="- Diverges from both stated targets.\n"
                "- Taking this role would make the next governance or programme step harder to "
                "argue for, not easier.",
         comp='- Base salary: "$180,000 — $230,000 USD" (stated).\n'
              "- Equity: \"meaningful equity\" — no figure, so **not stated**.\n"
              "- Comfortably above the recorded target. Compensation is not the problem here.",
         workload='- On-call: "participates in a weekly on-call rotation" — quoted.\n'
                  '- Reporting line: "reports to the Director of Platform Engineering" — quoted.\n'
                  "- Team size and travel: not stated.",
         gaps="### Confirmed Gaps\n\n"
              "- Daily hands-on development conflicts with an explicit stated limit.\n\n"
              "### Not Documented\n\n"
              "- Distributed systems design.\n"
              "- Production on-call ownership.\n\n"
              "### Questions for Recruiter\n\n"
              "- None. The constraint is dispositive and no answer would change it.",
         rectext="Skip. Well compensated, legitimately interesting, and a good role for someone "
                 "else. The day-to-day is the one thing this candidate has ruled out, and a high "
                 "salary is not a reason to overrule a stated limit."),

    dict(co="Ashgrove Health", title="Senior Program Manager, Clinical Data Platform",
         url="https://example.com/ashgrove/spm-clinical-data", loc="Remote — US (EST hours)",
         wp="Remote", jt="Full-time", src="Lever", score=72, rec="good",
         verdict="explore", want="medium", dirn="lateral", down=False,
         elig=[("US work authorisation", '"Authorised to work in the US"', "Met"),
               ("Remote work", '"Remote, core hours 9–5 Eastern"', "Met"),
               ("6+ years programme management",
                '"6+ years managing technical programmes."', "Met"),
               ("Healthcare or regulated-industry experience",
                '"Experience in healthcare, life sciences or another regulated industry."',
                "Met")],
         comps=[("Programme delivery in a regulated environment", "yes", "yes", "Foundational",
                 "Demonstrated",
                 'POSTING: "deliver against HIPAA and internal audit requirements". PROFILE: '
                 '"ran governance and audit programmes against external frameworks" [R] — '
                 "regulated delivery is evidenced, the regulation differs"),
                ("Stakeholder management across clinical and engineering teams", "no", "yes",
                 "Foundational", "Demonstrated",
                 'PROFILE: "coordinated across 9 organisations with no reporting authority" [R]'),
                ("HIPAA and clinical data handling specifically", "yes", "yes", "Foundational",
                 "Transferable",
                 "PROFILE evidences SOC 2 and ISO-style control work; HIPAA is a different "
                 "regime with different obligations and is not evidenced by name"),
                ("Data platform or pipeline programme experience", "no", "yes", "Foundational",
                 "Not Documented", "not evidenced in PROFILE"),
                ("Clinical trial operations", "no", "no", "Learnable", "Not Documented",
                 'POSTING lists as "a plus"')],
         readiness="Partly. Regulated-environment programme delivery is demonstrated and is the "
                   "harder half of this job. What is not evidenced is the specific regime — HIPAA "
                   "and clinical data handling — which the posting treats as defining. The "
                   "candidate could almost certainly learn it; they cannot currently claim it.",
         transfer="The transfer here is regime-to-regime rather than skill-to-skill. Running a "
                  "programme against SOC 2 and ISO-style controls teaches you how to work when an "
                  "external body will test your evidence, which is the same muscle HIPAA work "
                  "uses. It does not teach you HIPAA's specific obligations, and this assessment "
                  "does not pretend otherwise.",
         pref="- Remote, but with \"core hours 9–5 Eastern\" — a real constraint for a candidate "
              "in a western timezone, and the posting is explicit about it.\n"
              "- The work is governance-adjacent programme delivery, which fits the stated "
              "preference.\n"
              "- No daily development work described.",
         career="- Lateral rather than advancing: it uses the candidate's existing strengths in "
                "a new domain rather than deepening a stated target.\n"
                "- Healthcare regulatory experience would be genuinely additive if the candidate "
                "wants to widen into regulated industries.",
         comp='- Base salary: "$130,000 — $160,000 USD" (stated).\n'
              "- Bonus: \"annual performance bonus\" — no percentage, so **not stated**.\n"
              "- The band overlaps the candidate's recorded target of $135,000 – $165,000 but "
              "does not clear it; the bottom of the band sits below the target floor.",
         workload='- Core hours: "core hours 9–5 Eastern" — quoted. The single most important '
                  "workload line in this posting for a remote candidate.\n"
                  '- Reporting line: "reports to the Director of Clinical Platform" — quoted.\n'
                  '- Cadence: "two major releases per year" — quoted.\n'
                  "- On-call and travel: not stated.\n"
                  "- Team size: not stated.",
         gaps="### Confirmed Gaps\n\n"
              "- None, though the Eastern core-hours requirement is a stated condition worth "
              "weighing as one.\n\n"
              "### Not Documented\n\n"
              "- HIPAA and clinical data handling by name.\n"
              "- Data platform or pipeline programmes.\n"
              "- Clinical trial operations.\n\n"
              "### Questions for Recruiter\n\n"
              "- How strictly are the Eastern core hours enforced for a western-timezone hire?\n"
              "- Is HIPAA experience required at hire, or is a regulated-industry background "
              "sufficient?\n"
              "- Where does the bonus sit as a percentage of base?",
         rectext="Explore. The transferable half of this role is strong and honestly evidenced, "
                 "and the domain gap is learnable rather than disqualifying. The two things that "
                 "would decide it — core hours and whether the base can reach the target — are "
                 "both unresolvable from the posting, which is exactly what a first call is for."),
]

# md() in report.py is line-based: every source line becomes its own paragraph,
# list item or table row. Research prose therefore has to be stored one paragraph
# per line, unwrapped, or it renders as a stack of orphaned sentences. The lines
# are long on purpose.
def research_doc(company, role, blocks):
    L = [f'Below is the concise, factual research on {company} and the {role} role. All claims '
         f'are directly sourced; where data is absent, I note "not found."',
         "",
         "**Every company, figure and source on this page is invented for the demo.** The domains "
         "all resolve to example.com, which exists for exactly this purpose.",
         ""]
    for head, lines in blocks:
        L += ["---", "", f"**{head}**", ""] + lines + [""]
    return "\n".join(L)


RESEARCH = [
    dict(idx=0, usd=0.0449, intok=17600, outtok=1150, text=research_doc(
        "Northwind Analytics", "Senior Technical Program Manager, Trust & Safety", [
        ("1. COMPANY STAGE, SIZE, OWNERSHIP & MATERIAL NEWS (LAST 6 MONTHS)", [
            "- Company stage & ownership: Northwind Analytics is a private, venture-backed company founded in 2017, headquartered in Minneapolis. Series C closed March 2026, led by an existing investor ([example-filings.example.com](https://example-filings.example.com/northwind/series-c)).",
            "- Size: 410 employees as of the Series C announcement ([example-news.example.com](https://example-news.example.com/northwind-series-c)). A hiring tracker shows headcount at 437 in September 2026, a 6.6% increase over six months ([example-tracker.example.com](https://example-tracker.example.com/northwind)).",
            "- Material news (past 6 months):",
            "- In April 2026, Northwind announced Trust & Safety as a standalone organisation, previously split between Legal and Support ([example-news.example.com](https://example-news.example.com/northwind-trust-safety)).",
            "- In June 2026, the company published its first transparency report ([example-blog.example.com](https://example-blog.example.com/northwind-transparency-2026)).",
            "- No layoffs, acquisitions or leadership departures found in the period. Not found: any public statement about profitability or runway.",
        ]),
        ("2. DAY-TO-DAY FUNCTION OF THIS ROLE (BEYOND POSTING WORDING)", [
            "The posting describes defining escalation paths, briefing leadership weekly, and driving programmes across Policy, Engineering and Legal ([example.com](https://example.com/northwind/tpm-trust-safety)).",
            "",
            "However, real-world scope for this shape of role usually also includes:",
            "",
            "- **Owning the incident retrospective process** — the posting's reference to partnering with on-call engineering during incidents implies the TPM runs the review afterwards, not the response itself.",
            "- **Policy translation** — the April reorganisation moved Trust & Safety out of Legal, which typically leaves a TPM converting legal language into operational rules for the first year.",
            "- **Metrics definition from scratch** — the transparency report is the company's first, so the measures behind it are likely still being argued about rather than inherited.",
        ]),
        ("3. PUBLISHED COMPENSATION DATA (U.S.): BASE VS OTE/EQUITY", [
            "- The job posting lists a **national base salary range of $140,000–$175,000 USD**, and does not mention equity or bonus ([example.com](https://example.com/northwind/tpm-trust-safety)).",
            "- An aggregator reports a median base of **$152,000** for senior TPM roles at companies of this size, with equity eligibility at ~58% of respondents ([example-salary.example.com](https://example-salary.example.com/tpm-senior)). Where the aggregator and the posting disagree, both figures are shown rather than one being silently chosen.",
            "- Not found: any Northwind-specific equity structure or refresh policy.",
        ]),
        ("4. AMBIGUOUS QUALIFICATIONS IN POSTING & WHAT WOULD RESOLVE THEM", [
            "From posting:",
            "",
            '- "7+ years running technical programmes, or equivalent experience in a related field." → Ambiguous: what counts as a related field? Clarification: whether governance, risk or compliance programme work is accepted on its own.',
            '- "Partners with on-call engineering during incidents." → Ambiguous: does the TPM join the rotation? Clarification: whether this role carries a pager.',
            '- "Experience with trust & safety preferred." → Ambiguous: preferred over what, and how heavily weighted against the programme-management requirement stated as mandatory.',
            '- "Occasional evening coverage during a major incident." → Ambiguous: frequency. Clarification: how many major incidents occurred in the last two quarters.',
        ]),
        ("5. FOUR SPECIFIC QUESTIONS TO ASK RECRUITER ABOUT THIS ROLE", [
            '1. "The Trust & Safety org became standalone in April — what moved with it, and what is still owned by Legal?"',
            '2. "Does this TPM carry a pager, or partner with the people who do?"',
            '3. "The transparency report was the company\'s first. Who defines the measures behind the next one?"',
            '4. "Is equity part of the package at this level, and is the base band national or location-adjusted?"',
        ]),
    ])),
    dict(idx=1, usd=0.0461, intok=18050, outtok=1190, text=research_doc(
        "Vance Maritime Group", "Director, Security Governance & Compliance", [
        ("1. COMPANY STAGE, SIZE, OWNERSHIP & MATERIAL NEWS (LAST 6 MONTHS)", [
            "- Company stage & ownership: Vance Maritime Group is a privately held logistics and port services operator founded in 1998, headquartered in Norfolk, Virginia. Majority stake acquired by a mid-market private equity fund in January 2026 ([example-filings.example.com](https://example-filings.example.com/vance/acquisition)).",
            "- Size: approximately 2,900 employees across 11 sites ([example-tracker.example.com](https://example-tracker.example.com/vance)).",
            "- Material news (past 6 months):",
            "- In February 2026, Vance disclosed a vendor-related security incident affecting scheduling systems at two ports; no customer data was reported compromised ([example-news.example.com](https://example-news.example.com/vance-incident)).",
            "- In May 2026, the company stated it was pursuing SOC 2 Type II for the first time, naming it a customer requirement ([example-blog.example.com](https://example-blog.example.com/vance-soc2)).",
            "- Not found: any public statement on the outcome of the February incident review.",
        ]),
        ("2. DAY-TO-DAY FUNCTION OF THIS ROLE (BEYOND POSTING WORDING)", [
            "The posting describes owning the governance programme, leading SOC 2 Type II and ISO 27001 cycles, and leading a team of three ([example.com](https://example.com/vance/dir-security-governance)).",
            "",
            "Context the posting does not state:",
            "",
            "- **This is a first-time audit.** The May announcement indicates SOC 2 Type II has not been achieved before, so the role is building the programme rather than maintaining one. That is substantially more work in year one and should be priced accordingly.",
            "- **The February incident is likely in scope.** A vendor-related incident six months before a first audit usually means third-party risk gets rebuilt at the same time — which matches the vendor risk line buried in the posting's responsibilities.",
            "- **Private-equity ownership one year in** generally means reporting obligations upward on a fixed cadence, in addition to the audit calendar.",
        ]),
        ("3. PUBLISHED COMPENSATION DATA (U.S.): BASE VS OTE/EQUITY", [
            '- The posting lists **$165,000–$200,000 USD base**, plus "participation in the company equity plan" with no structure given ([example.com](https://example.com/vance/dir-security-governance)).',
            "- Industry benchmark for Director-level GRC roles reports: average base salary **$178,000**; average annual cash compensation (base + target bonus) **$203,000**; equity eligibility ~31% of respondents at privately held firms ([example-salary.example.com](https://example-salary.example.com/grc-director)).",
            "- Note: equity at a PE-owned private company is a materially different instrument from startup equity, and the posting does not say which it is.",
        ]),
        ("4. AMBIGUOUS QUALIFICATIONS IN POSTING & WHAT WOULD RESOLVE THEM", [
            "From posting:",
            "",
            '- "8+ years in security GRC or a closely related field." → Ambiguous: does programme governance without a security title count? Clarification: examples of accepted backgrounds.',
            '- "Demonstrated experience delivering SOC 2, ISO 27001 or equivalent audits." → Ambiguous: delivering as owner, or contributing evidence? Clarification: the expected level of ownership.',
            '- "Lead a team of three." → Ambiguous: existing team or to be hired. Clarification: whether the three are in post today.',
            '- "Familiarity with GRC platforms preferred." → Ambiguous: which platform, and whether a migration is planned.',
        ]),
        ("5. FOUR SPECIFIC QUESTIONS TO ASK RECRUITER ABOUT THIS ROLE", [
            '1. "Is this the first SOC 2 Type II cycle, and what is the target date?"',
            '2. "Are the three analysts in post today, or is this role hiring them?"',
            '3. "How much of the February vendor incident\'s remediation sits with this role?"',
            '4. "Is the equity plan a traditional option grant, or a PE-style co-investment?"',
        ]),
    ])),
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

for n, r in enumerate(RESEARCH):
    j = JOBS[r["idx"]]
    research.append({
        "ts": (now - timedelta(minutes=10 + n)).isoformat(timespec="seconds"),
        "local_date": today, "url": j["url"], "company": j["co"], "jobTitle": j["title"],
        "model": "gpt-4.1", "usd": r["usd"],
        "input_tokens": r["intok"], "output_tokens": r["outtok"],
        "selected_by": {"verdict": j["verdict"], "desirability": j["want"],
                        "direction": j["dirn"]},
        "research": r["text"],
    })

(OUT / "queue.json").write_text(json.dumps(queue, indent=1))
(OUT / "assessments.jsonl").write_text("".join(json.dumps(a) + "\n" for a in assess))
(OUT / "research.jsonl").write_text("".join(json.dumps(r) + "\n" for r in research))
(OUT / "last-run.json").write_text(json.dumps({
    "ran_at": (now - timedelta(minutes=45)).isoformat(timespec="seconds"),
    "companies": 119, "fetched": 12548, "kept": len(JOBS), "created": len(JOBS),
    "skipped": 0, "mcp_calls": 9, "rate_limited": False,
    "fetch_errors": [], "push_errors": [], "ok": True}, indent=2))
(OUT / "spend.json").write_text(json.dumps(
    {"date": today, "calls": len(JOBS) + len(RESEARCH), "usd": 0.1915}, indent=2))
print(f"wrote {len(JOBS)} sample jobs and {len(RESEARCH)} research entries to {OUT}")
