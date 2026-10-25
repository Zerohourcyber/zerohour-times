# Tutorial: your own edition of The ZeroHour Times

Written for someone who has used a terminal a few times and is not a developer.
Takes about 20 minutes, most of it waiting for Docker.

If a step does not look like the description here, stop and read the error — it
usually says exactly what is missing.

---

## Before you start

You need:

- **Docker Desktop** (Mac/Windows) or Docker Engine (Linux) — <https://docs.docker.com/get-started/>
- **An OpenAI API key** — optional for now. Without one you still get discovery
  and the newspaper; you just do not get AI assessments or research.
- **A CV or résumé** you can refer to while filling in your profile.

Check Docker is running:

```bash
docker --version
```

## Step 0 — look around first (no keys, no account)

```bash
git clone https://github.com/Zerohourcyber/zerohour-times.git
cd zerohour-times
docker compose run --rm --no-deps --service-ports zerohour-times demo
```

Open <http://localhost:8099>. That is the newspaper, built from three fictional
jobs bundled with the project. Nothing was installed, no key was used, and no
data left your machine. Press `Ctrl+C` when you have seen enough.

## Step 1 — set up

```bash
./scripts/setup.sh
```

It asks a handful of questions and writes three files:

- **`.env`** — your secrets. It generates two for you.
- **`config.json`** — which employers to watch and which jobs to keep.
- **`profile.md`** — who you are.

> **Save your `ENCRYPTION_KEY` somewhere safe now.** It encrypts the API keys
> JobSync stores. If you lose it, those keys cannot be recovered — by design.

## Step 2 — start everything

```bash
docker compose up -d
```

Two containers start: **JobSync** (the job tracker) and **The ZeroHour Times**
(discovery, assessment, research, newspaper). First run pulls images, so give
it a few minutes.

Check they are healthy:

```bash
docker compose ps
```

## Step 3 — claim your JobSync account *immediately*

Open <http://localhost:3737> and create your account **now**.

> JobSync's signup is open by default and cannot be switched off. Whoever
> reaches that page first gets the account. It is bound to localhost, so this is
> a small window — but close it before doing anything else.

## Step 4 — connect the two systems

In JobSync: **Settings → MCP → create a token**.

- Scope: **`jobs:write`** and nothing else.
- Expiry: set one. A year is reasonable.
- **Name it something meaningful** — JobSync stamps the token's name onto every
  job it creates, so `zerohour-times` reads better in your records than `token1`.

Copy the token (it is shown once), then edit `.env`:

```
JOBSYNC_MCP_TOKEN=paste_it_here
```

While you are in there, add your OpenAI key if you have one:

```
OPENAI_API_KEY=sk-...
```

## Step 5 — write your profile

Run the profile builder — it asks plain questions and writes the structured file
for you:

```bash
python3 scripts/profile.py
```

This is the single most important file in the project: the AI assesses every job
against it and is instructed **never to claim anything that is not in it**. You
can edit `profile.md` directly afterwards; re-running the builder keeps a
timestamped backup of the old one.

Three rules that make it work:

1. **Tag every claim.** `[R]` from your résumé, `[O]` your own statement,
   `[?]` genuinely unknown. The `[?]` tag matters — an expired clearance marked
   `[?]` will not be asserted either way.
2. **Write outcomes, not duties.** "Reduced late submissions from 23 to zero in
   three months" beats "responsible for process improvement". The assessment is
   only as specific as the evidence you give it.
3. **Fill in "NOT DOCUMENTED" honestly.** List the things employers ask for that
   your CV does not evidence. This is what stops the AI inventing them, and it
   is what makes a gap report useful rather than flattering.

Then edit `config.json`:

- **`filters.titleAny` / `titleNone`** — describe the work you actually want.
- **`watchlist`** — five example employers ship by default. Replace them with
  companies you would actually work for. For a bigger starting point, there are
  119 verified boards in `starter-watchlist.json`; copy across the ones that fit.

## Step 6 — run it

```bash
docker compose restart zerohour-times
docker compose logs -f zerohour-times
```

You will see discovery fetch boards, matching assess new postings, research run
on the top few, and the newspaper rebuild. First run takes a few minutes.

Open <http://localhost:8099>.

## Reading your front page

- **Numbers across the top** — discovered, assessed, awaiting, researched, and
  how many are apply/explore.
- **Press Run** — whether each stage worked, and today's spend against your cap.
- **Situations Vacant** — every opening. Click one to read the full assessment.
- **Help Wanted** — the leading "apply" role, with the particulars, what is
  missing, and questions to ask a recruiter.

**Read the verdict and the reasoning, not the score.** The rejection logic is
reliable; the ranking of good matches is not. See
[AI-GOVERNANCE.md](AI-GOVERNANCE.md).

## Adding employers

```bash
cp employers.example.txt employers.txt      # edit, one company name per line
docker compose exec zerohour-times python3 /app/zhtimes/resolve.py \
    --names /app/employers.txt --merge /app/config.json
```

Only companies whose board actually returns postings are added. Many large
employers use Workday or SmartRecruiters, which this project does not read —
they will simply not resolve.

## When it runs

Daily at the time you chose (`ZHT_RUN_AT`, default 07:10 local). To run now:

```bash
docker compose exec zerohour-times python3 /app/zhtimes/run.py once
```

## Troubleshooting

| Symptom | Cause |
|---|---|
| "JOBSYNC_MCP_TOKEN is not set" | Step 4 incomplete, or you did not restart after editing `.env` |
| Newspaper is empty | No postings matched your filters — widen `titleAny` |
| "Rate limit exceeded" | JobSync allows 100 MCP calls/hour. Normal with a big watchlist; the deferred jobs go in next run |
| Assessments not appearing | No `OPENAI_API_KEY`, or the daily cap was reached |
| "Discovery failed" on the page | Read the log: `docker compose logs zerohour-times` |

## Stopping and starting

```bash
docker compose stop     # pause
docker compose up -d    # resume
docker compose down     # stop and remove containers (your data volumes survive)
```
