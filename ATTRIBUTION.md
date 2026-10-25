# Attribution

## JobSync — not part of this project

**The ZeroHour Times does not include, fork, or modify JobSync.**

[JobSync](https://github.com/Gsync/jobsync) is an open-source AI job-search
platform by **[Gsync](https://github.com/Gsync)**, released under the MIT
licence. It is an excellent piece of software and all credit for it belongs to
its author.

This project runs JobSync **unmodified, from its official published image**
(`ghcr.io/gsync/jobsync`), and integrates with it only through the **MCP
interface JobSync itself publishes** — `add_jobs_batch`, `find_job` and
`save_match_result`, authenticated with a scoped bearer token you mint in
JobSync's own UI.

That boundary is deliberate and is the central design decision of this project:

- **No fork.** Upgrading JobSync is a tag bump in `docker-compose.yml`, not a merge.
- **No schema changes.** JobSync owns its database; this project never writes to it.
- **No scraping of its internals.** Only documented tools are called.
- **JobSync stays the system of record** for your applications and saved assessments.

If you find this project useful, please star
[Gsync/jobsync](https://github.com/Gsync/jobsync) too. Without it there is
nothing here to integrate with.

### Why not fork it?

JobSync once had a keyword-search job source and **removed it** in v1.1.19,
narrowing deliberately to first-party ATS boards. A fork re-adding that would
re-introduce exactly what upstream deleted, in exactly the files they changed,
on every single upgrade. Building the discovery layer *outside* the app and
talking to it through its published interface costs one env var
(`MCP_ENABLED=true`) and survives upgrades untouched.

## Job board APIs

Greenhouse, Lever and Ashby each publish open roles through a public, keyless
JSON API, which is what this project reads:

- `boards-api.greenhouse.io/v1/boards/{token}/jobs`
- `api.lever.co/v0/postings/{token}`
- `api.ashbyhq.com/posting-api/job-board/{token}`

**Public access is not republication rights.** Employers retain copyright on
their job descriptions. Reading these endpoints for your own job search — an
agent acting on your behalf — is what they are for. Redistributing the content,
reselling it, or republishing descriptions is a different thing and is your
responsibility to get right. Poll politely: these are free endpoints run for
employers, not for us.

## AI provider

Assessment and research call an OpenAI-compatible API with **your** key, which
stays in your `.env` and is never committed. Any compatible endpoint works via
`OPENAI_BASE_URL`.
