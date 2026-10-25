# How this AI system is evaluated, governed and monitored

This document exists because an AI tool that scores your career options should
be held to a higher standard than "the output looks good." It records what the
system does, how it was tested, **what it got wrong**, and what is still unknown.

If you are evaluating this project, this is the file to read.

---

## 1. The risk being managed

The system asks a language model to judge whether a person can do a job, then
shows that judgement to a human making a consequential decision. Three failure
modes matter, in order:

1. **Agreeable scoring** — telling the user they are qualified for everything,
   which makes the tool useless and wastes their time on bad applications.
2. **Fabrication** — asserting a credential, a salary, or a remote policy that
   no source supports.
3. **Injection** — a job posting or a web page instructing the model, because
   both are attacker-controlled input.

Each is addressed by a specific mechanism below, not by prompt wording alone.

## 2. What actually went wrong

Recorded because the failures are more informative than the fixes.

### Every role scored 85–92 "strong"

The first version rated five very different roles within seven points of each
other, all "strong". The clearest failure: a partner-channel programme role
scored **85/strong** while its *own analysis* listed partner programme
management, partner enablement and PRM tooling as "not documented" — the three
things the job exists to do.

**Cause:** broad transferable experience was treated as sufficient without
checking whether the candidate could perform the role's central work.

### Fixing it created a worse failure

Loosening how competencies were counted let the model enumerate every posting
requirement and grade them generously. The same partner role moved
**57/partial → 92/strong** by reclassifying its defining competency from
*Not Documented* to *Demonstrated*, generalising from ordinary programme
management.

**Lesson, and the reason the validator exists:** the binding constraint was
never the rubric or the thresholds. It was **what the model was allowed to call
"Demonstrated."**

### A one-time onboarding trip rejected a good job

A posting said *"all go-to-market roles will have an in-person onboarding in
Toronto."* The model treated that as an ongoing location requirement and
**skipped a role it had just scored 88**.

**Fix:** eligibility now means *structural, ongoing* requirements only. One-off
onboarding, occasional travel and annual offsites are reported under workload,
never used to reject. The offending boilerplate is quoted in the prompt as a
counter-example.

### An internship scored 90

Correct on pure qualification — the candidate is overqualified — and useless as
advice. Internship and explicitly junior titles are now capped by a
deterministic title check, independent of the model's judgement.

### A formatting bug destroyed five paid assessments

A field-name error in the report writer crashed *after* five API calls, losing
all five analyses. **Fix:** full output is appended to the log the moment it
returns, before any formatting runs, and the report builder cannot take the
process down. Paid output is never held only in memory.

## 3. Evaluation

### The adversarial set

Tuning against promising jobs only tests the ceiling. `zhtimes/calibset.py`
builds a validation set that deliberately samples the floor:

| Category | Why it is there |
|---|---|
| Hands-on engineering roles | Should be rejected on a stated preference |
| Explicitly junior / internships | Qualified but inappropriate |
| Non-remote and hybrid | Violates a hard constraint |
| Misleading titles | "Program Manager" whose duties are writing code |
| Mandatory credentials absent | A JD with an active bar, etc. |
| Defining competency outside the profile | Partner/channel, M&A, GTM |
| Genuine target roles | The ceiling |

### Measured results

23 postings across 8 categories:

| | |
|---|---|
| Mandatory-qualification roles | **3/3 correctly rejected** |
| Misleading titles | **3/3 rejected** |
| Non-remote | **3/3 rejected** |
| Hands-on engineering | 2 partial, 1 weak — all marked low desirability |
| Genuine targets | **3/3 strong** |
| False "strong" | **1 of 23** (an internship — since fixed) |
| Incorrect skips | **2 of 23** (travel boilerplate — since fixed) |
| Eligibility accuracy | **7 of 9** correct |

**The floor is reliable. The ceiling is not.** Across prompt versions, the same
role moved as much as three bands. Only one of five tracked roles was stable.

That is why the product shows **apply / explore / skip and the reasoning**, and
treats the number as advisory.

## 4. Governance mechanisms

| Control | Implementation |
|---|---|
| **Structured evidence** | The model must emit a competency table with status and citation per row; an unparseable table is an error and the result is discarded, not saved. |
| **Deterministic override** | `validate()` caps the rating when the model's own structured claims contradict its score. Defining competency undocumented → `partial`. Transferable only → `good`. Confirmed gap → `partial`. Eligibility not met → `weak`. Junior title → `partial`. |
| **Transparency** | Every automated downgrade is written into the saved assessment, naming the rule and the competency. Silent correction would be worse than none. |
| **Evidence or silence** | Claims must cite the posting or the profile. Unstated salary, location, team size and on-call stay "not stated". |
| **Absence ≠ deficit** | "Not documented" and "confirmed gap" are separate statuses and may never be collapsed. |
| **Prompt versioning** | Every assessment records the prompt version and model, so any score traces to the exact instructions that produced it. |
| **No overwrite** | Existing assessments are never replaced without an explicit flag; JobSync stores one match per job and there is no history table. Assessments made by hand are detected and left alone. |
| **Untrusted input** | Research runs stateless, with one tool (`web_search`) and no credentials. Output is stored and rendered, never executed, never used to select a tool, never written back. Model text is HTML-escaped before any markup is applied. |
| **Spend ceiling** | A hard daily cap, keyed to local date, shared by assessment and research, enforced in code. |
| **Rate limiting** | Treated as a failure, never as success. A throttled run exits non-zero and records what was not saved. |

## 5. Monitoring

- `assessments.jsonl` — append-only: timestamp, model, prompt version, token
  counts, cost estimate, the model's original score, the validated score,
  whether a downgrade fired, the full analysis.
- `spend.json` — running daily cost and call count.
- `last-run.json` — per-stage health, surfaced on the dashboard front page.
- The dashboard prints each stage as `ok` / `stale` / `failed` with its age, so
  a silent failure is visible rather than absent.

## 6. What is still unknown

Stated because a governance document that only lists successes is marketing.

- **Run-to-run variance on identical input has never been measured.** All
  observed variance is between prompt versions. A scoring engine that moves a
  band between identical runs cannot be trusted to rank, and this experiment has
  not been done.
- **Ranking remains unstable** between prompt revisions.
- **One human evaluator.** Agreement was measured against a single person's
  judgement on five roles — enough to catch gross miscalibration, not enough to
  claim accuracy.
- **No bias evaluation.** The system scores one profile against many postings;
  it has not been tested for systematic differences across candidate
  characteristics, and should not be used to screen other people.
- **The model is not fine-tuned or distilled.** Provider changes can shift
  behaviour without notice — which is exactly why the deterministic validator
  sits downstream of it.

## 7. If you are building something similar

The three things that mattered most, in order:

1. **Make the model show its work in a structure you can parse**, then check the
   structure in code. Prose confidence is not evidence.
2. **Test the floor, not the ceiling.** Five promising examples will tell you
   everything is fine.
3. **Write down the failures.** Every fix above came from a run that looked
   successful until someone read it carefully.
