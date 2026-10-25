# Release testing

What has been verified, what has not, and how to close the gap — using a
**disposable test instance**, never a JobSync you already rely on.

## Use a throwaway instance

Run the test from a **fresh clone in a separate folder**. It gets its own Docker
volumes, its own JobSync database, its own account. Nothing it does can reach an
existing instance.

```bash
git clone https://github.com/Zerohourcyber/zerohour-times.git ~/zht-test
cd ~/zht-test
./scripts/setup.sh
docker compose -p zht-test up -d
```

The `-p zht-test` names the project, so its containers, network and volumes are
separate from any other copy on the same machine. Use the **same `-p` flag for
every command below**, or Compose will act on the wrong stack.

> If you already run JobSync on this machine, change `JOBSYNC_PORT` and
> `ZHT_DASHBOARD_PORT` in `.env` first so the test cannot collide with it.

**Create a test account** in the test instance with a throwaway email — do not
reuse the credentials of an instance holding your real job search.

When you are done:

```bash
docker compose -p zht-test down -v     # -v removes the test volumes too
```

## What has already been verified

Automated, free, repeatable — these run in CI on every push:

| | |
|---|---|
| Setup wizard from a fresh clone | Pass |
| `docker compose up --build`, both healthy | Pass |
| Isolation: own volumes, ports on `127.0.0.1` | Pass |
| Demo mode with no key and JobSync stopped | Pass |
| Graceful degradation with no MCP token | Pass |
| Persistence across restart | Pass |
| Scheduler honours the configured timezone | Pass |
| MCP rejects unauthenticated calls | Pass |
| Secret scan, stdlib-only check, render assertions | Pass |

## What is NOT yet verified

Everything downstream of the browser, because JobSync has no API for account
creation or token minting:

- a token minted in the UI actually authenticates
- discovery pushes real postings into JobSync
- an assessment is produced, validated and saved
- research produces a sourced report
- the newspaper renders real jobs

The two steps below close that gap.

## Step 1 — the browser steps (5 minutes, free)

Follow **[CONNECT-JOBSYNC.md](CONNECT-JOBSYNC.md)**: create the account, mint a
token scoped to `jobs:write`, paste it into `.env`, restart.

Then confirm, still spending nothing:

```bash
docker compose -p zht-test logs zerohour-times | tail -20
```

`# queued N posting(s) for matching` means the token works and discovery ran.
At this point jobs exist in JobSync with no assessments — matching is skipped
without an AI key, which is the correct behaviour.

## Step 2 — the capped smoke test (~$0.11)

```bash
./scripts/smoke-test.sh                 # dry run: checks everything, spends nothing
./scripts/smoke-test.sh --i-will-pay    # the real thing
```

It caps itself at **3 assessments and 1 research call under a $0.25 ceiling**,
writing a temporary config for the run and restoring yours afterwards. It then
checks:

| Stage | Assertion |
|---|---|
| Discovery | a queue was written |
| Assessment | `SCORES`, `VERDICT` and a competency table are present; prompt version and cost recorded; verdict parses |
| Validation | reports any downgrade, with the model's original rating beside the validated one |
| Research | a report was produced containing source links |
| Newspaper | renders with real notices, verdict badges and working links |
| Spend | prints actual cost against the cap |

Expected: **about $0.11**. The dry run refuses to proceed if anything is
missing, so run that first.

## After it passes

```bash
docker compose -p zht-test down -v
```

Your real instance, if you have one, was never involved.
