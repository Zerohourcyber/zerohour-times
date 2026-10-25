# Release checklist — v1.0

Everything here is deliberate: this file is deleted or emptied at release, not
left as decoration.

## Blocking — must be done before the repository is public

- [ ] **Capture the screenshot.** `docs/images/newspaper.png`, from **demo
      data** only — see [docs/images/README.md](docs/images/README.md). Then
      uncomment the image line at the top of [README.md](README.md).
      *(A screenshot of a real edition would publish your job search.)*
- [x] ~~Replace the GitHub account placeholder~~ — now
      `github.com/Zerohourcyber/zerohour-times` throughout.
- [ ] **Live integration test.** Follow [docs/TESTING.md](docs/TESTING.md) on a
      throwaway instance: create the account, mint a token, confirm discovery
      pushes real postings.
- [ ] **Capped smoke test.** `./scripts/smoke-test.sh --i-will-pay` (~$0.11),
      confirming assessment, validation, research and rendering end to end.
- [ ] **Confirm the LICENSE name** is how you want to be credited.

## Verified already

- [x] Setup wizard from a fresh clone
- [x] `docker compose up --build` with the official JobSync image
- [x] Isolation: dedicated volumes, ports on `127.0.0.1`
- [x] Demo mode with no API key and JobSync stopped
- [x] Graceful degradation with no MCP token
- [x] Persistence across container restart
- [x] Scheduler honours the configured timezone
- [x] MCP rejects unauthenticated requests
- [x] Secret scan clean across every tracked file
- [x] stdlib-only (no dependency to install)
- [x] Dashboard render assertions
- [x] No broken internal documentation links
- [x] Commands consistent across wizard, docs and CI

## Deliberately not in v1.0

Recorded so they are choices rather than oversights:

- **Run-to-run scoring variance is unmeasured.** Documented in
  [AI-GOVERNANCE.md](docs/AI-GOVERNANCE.md) rather than hidden.
- **Only Greenhouse, Lever and Ashby.** Workday, SmartRecruiters and Workable
  are not supported.
- **The dashboard is unauthenticated.** Read-only and localhost-bound by
  default; see [SECURITY.md](SECURITY.md).
- **No email or notifications.** The newspaper is the interface.
- **No multi-user support.** One person, one machine, by design.
