# Security and privacy

This project reads untrusted web content, holds an API key, and generates
analysis of your career. Here is exactly what that means and what protects you.

## Your data stays on your machine

Everything lives in Docker volumes on the host you run it on. There is no
telemetry, no analytics, no phone-home, and no account with this project — it
has no server to talk to.

| What | Where | Leaves your machine? |
|---|---|---|
| Your profile (`profile.md`) | bind-mounted, gitignored | **Only** as part of an AI assessment prompt |
| Your CV, applications, statuses | JobSync's volume | No |
| Assessments and research | `/data` volume | No |
| API keys | `.env`, gitignored | To your AI provider only, as auth |

**The one exception worth understanding:** each assessment sends your profile
and one job posting to your AI provider, and each research call sends the
company and role to the provider, which performs a web search. If that is not
acceptable, leave `OPENAI_API_KEY` blank — discovery and the newspaper still
work, you simply get no AI assessments.

## Known exposure

### The dashboard is unauthenticated

It is read-only, but **anyone who can reach the port can read your assessments
and profile-derived analysis**. It binds to `127.0.0.1` by default. If you
change `ZHT_DASHBOARD_BIND`, put it behind something — a VPN such as Tailscale,
an authenticating reverse proxy, or an SSH tunnel. Do not put it on the open
internet.

### JobSync's signup cannot be disabled

JobSync (not this project) allows open registration and offers no setting to
turn it off. Whoever reaches it first gets the account. **Claim yours the moment
you first start it**, and keep it bound to localhost or a private network. This
is an upstream design decision, documented here because it is the sharpest edge
in the stack.

### Secrets

`.env`, `profile.md` and `config.json` are gitignored. `scripts/scan-secrets.py`
runs in CI on every push and fails the build on anything key-shaped, plus a
private IP, a private-key block, or a tracked private file. Run it locally
before you commit:

```bash
python3 scripts/scan-secrets.py
```

**`ENCRYPTION_KEY` cannot be recovered.** JobSync uses it to encrypt the
provider keys it stores. Losing it loses them — by design. Keep a copy
somewhere safe before you enter any API key.

**Scope your MCP token.** `jobs:write` is all this project needs. Give it an
expiry. Its name is stamped onto every job it creates, so name it meaningfully.

## Untrusted input

Job postings and the web pages behind them are written by other people and must
be treated as hostile:

- **Research is stateless, with one tool and no credentials.** It can search the
  web and return text. It cannot call another tool, write to JobSync, read your
  files, or persist anything between runs.
- **Model output is never executed.** It is stored, parsed for a known structure,
  and rendered. It is HTML-escaped *before* any markdown is applied, so no tag
  in model output can become markup.
- **Nothing the model says can change a record.** Assessments are written through
  one narrow tool with a validated payload; research is never written back at all.

The worst outcome of a successful prompt injection is a misleading paragraph in
a report a human reads. That is a deliberate design ceiling, not an accident.

## Spending

A hard daily cap, keyed to your local date, shared by assessment and research,
enforced in code — the run stops when it is reached. Set it in `config.json` →
`matching.max_usd_per_day`. Token prices are configurable there too and **must**
be checked against your provider's current pricing; they produce an estimate,
not a bill.

## Being a good citizen of other people's APIs

Board endpoints are free and run for employers, not for us. Requests are paced,
and `resolve.py` sleeps between probes. Please do not remove that. Public access
is not republication rights: employers retain copyright on their job
descriptions. Reading them for your own job search is what these endpoints are
for; redistributing them is not.

## Reporting a vulnerability

Open a GitHub issue for anything non-sensitive. For something that should not be
public, use GitHub's private vulnerability reporting on the repository rather
than an issue.
