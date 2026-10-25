# Architecture

Two containers. One is ours, one is not.

```mermaid
flowchart TB
    subgraph boards["Public employer job boards — free, keyless, first-party"]
        GH["Greenhouse<br/>boards-api.greenhouse.io"]
        LV["Lever<br/>api.lever.co"]
        AB["Ashby<br/>api.ashbyhq.com"]
    end

    subgraph zht["The ZeroHour Times — this project"]
        direction TB
        D["discover.py<br/><i>poll · filter · dedupe</i>"]
        M["match.py<br/><i>assess · validate</i>"]
        R["research.py<br/><i>web-grounded context</i>"]
        P["report.py<br/><i>build the newspaper</i>"]
        D --> M --> R --> P
    end

    subgraph js["JobSync — Gsync, MIT, UNMODIFIED"]
        MCP["/api/mcp<br/><i>add_jobs_batch · find_job<br/>save_match_result</i>"]
        DB[("SQLite<br/>system of record")]
        UI["Web UI<br/><i>you claim the account here</i>"]
        MCP --- DB --- UI
    end

    AI["AI provider<br/><i>your key, your spend cap</i>"]
    WEB["The open web<br/><i>untrusted input</i>"]
    YOU(["Your browser<br/>localhost:8099"])

    GH & LV & AB -->|"read only"| D
    D -->|"push new postings"| MCP
    M <-->|"jobId · is it scored?"| MCP
    M -->|"save assessment"| MCP
    M -.->|"one call per new posting"| AI
    R -.->|"one call, web_search only"| AI
    R -.->|"reads"| WEB
    P --> YOU
    UI --> YOU

    classDef ours fill:#e8f0fe,stroke:#1f4fd8,stroke-width:2px
    classDef theirs fill:#fdf3e0,stroke:#8a6318,stroke-width:2px
    classDef ext fill:#f1f2f4,stroke:#6b7280,stroke-dasharray:4 3
    class D,M,R,P ours
    class MCP,DB,UI theirs
    class GH,LV,AB,AI,WEB ext
```

## What belongs to whom

| Component | Owner | Licence |
|---|---|---|
| `zhtimes/*`, prompts, dashboard, docs | **This project** | MIT |
| JobSync (image, UI, database, MCP server) | [Gsync](https://github.com/Gsync/jobsync) | MIT — **unmodified, not forked** |
| Greenhouse / Lever / Ashby board APIs | Those companies | Public endpoints; read-only use |
| The AI model | Your provider | Your key, your account, your spend |

## Why the boundary sits where it does

**JobSync is the system of record.** It owns your applications, statuses and
saved assessments. This project never writes to its database, never reads it,
and never forks it — it talks only through the MCP tools JobSync publishes.
Upgrading JobSync is a tag bump in `docker-compose.yml`.

**The stages are independent.** Discovery costs nothing and needs no AI.
Matching needs an AI key. Research needs an AI key and the web. Each runs in its
own subprocess; one failing does not stop the others, and the newspaper is
rebuilt either way so a failure is visible on the page rather than silently
absent.

**The trust boundary is around the model, not inside it.** Job postings and web
pages are attacker-controlled. The research stage is stateless, has exactly one
tool, and holds no credentials. Its output is stored and displayed — never
executed, never used to pick a tool, never written back into JobSync. Model text
is HTML-escaped before any markup is applied. A successful prompt injection
achieves a misleading paragraph in a report a human reads, and nothing else.

**Code checks the model.** `validate()` reads the structured claims the model
makes about its own evidence and caps the rating when they contradict its score.
See [AI-GOVERNANCE.md](AI-GOVERNANCE.md).

## Data flow in one pass

1. `discover.py` polls each watchlist board, applies your filters, drops local
   duplicates, pushes new postings into JobSync (`add_jobs_batch`, which upserts),
   and writes a queue for the next stage.
2. `match.py` asks JobSync which queued postings exist and whether they already
   carry an assessment (`find_job`), scores only the new ones, runs the validator,
   and saves results (`save_match_results_batch`). Existing assessments are never
   overwritten without an explicit flag.
3. `research.py` picks up to three by verdict and preference — never by score —
   and gathers web-grounded company context, cached so nothing is paid for twice.
4. `report.py` reads only this project's own files and writes `index.html` and
   `report.json` atomically.

## State

No database of our own. One directory, one volume:

```
/data/
  queue.json              today's candidate postings
  assessments.jsonl       append-only: every assessment, with cost and prompt version
  research.jsonl          append-only: every research call
  seen.json               URLs already pushed, so lookups scale with new postings
  externally-scored.json  jobs assessed by hand in JobSync — never touched
  spend.json              daily spend and call count
  www/index.html          the newspaper
```
