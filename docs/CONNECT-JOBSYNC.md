# Connecting JobSync — the browser steps

Almost all of this project runs without you. **Four things must happen in a
browser**, because JobSync has no API for them. This page is exactly those four,
with nothing else in the way.

Total time: about five minutes.

---

## Before you start

JobSync must be running:

```bash
docker compose up -d
docker compose ps        # both services should say "healthy"
```

---

## ① Create your account — do this *first*, and immediately

Open **<http://localhost:3737>**

You will see a sign-in page with a **Register** (or *Sign up*) link.

1. Click **Register**.
2. Enter your name, email and a password. The email does not need to be real or
   verified — nothing is sent anywhere. Use a password manager.
3. Submit. You are signed in.

> **Why "immediately":** JobSync allows open registration and provides no way to
> turn it off. Whoever reaches that page first gets the account. It is bound to
> `127.0.0.1` so the window is small — but close it before doing anything else.
> This is an upstream design choice, not something this project can change.

---

## ② Create the MCP token

This is the credential The ZeroHour Times uses to put jobs into JobSync. It is
the only thing the two systems share.

1. In JobSync, open **Settings** (usually the gear icon or your avatar menu).
2. Find the **MCP** section.
3. Click **Create token** / **New token**.
4. Fill it in:
   - **Name:** `zerohour-times`
     *(JobSync stamps this name onto every job the token creates, so a
     meaningful name gives you a free audit trail. "token1" does not.)*
   - **Scopes:** tick **`jobs:write`** and **nothing else.** That is all this
     project needs. If `questions:write` or `resume:write` are ticked by
     default, untick them.
   - **Expiry:** set one. A year is sensible.
5. Click create.

**The token is shown once.** Copy it now. If you lose it, delete it and make
another — you cannot retrieve it.

---

## ③ Paste the token into `.env`

Back in your terminal, in the project folder:

```bash
nano .env          # or any editor
```

Find this line and paste after the `=`, with no quotes and no spaces:

```
JOBSYNC_MCP_TOKEN=paste_the_token_here
```

Save and exit *(nano: Ctrl-O, Enter, Ctrl-X)*. Then:

```bash
docker compose restart zerohour-times
docker compose logs -f zerohour-times
```

You should see discovery start fetching boards instead of
`JOBSYNC_MCP_TOKEN is not set`. Press Ctrl-C to stop watching the log.

---

## ④ Upload your CV to JobSync *(optional)*

JobSync can store and parse your résumé for its own features. **The ZeroHour
Times does not use it** — assessments are made against `profile.md`, which you
create with `python3 scripts/profile.py`.

Upload it if you want JobSync's own résumé tools. Skip it otherwise; nothing in
this project depends on it.

---

## A point of confusion worth clearing up

**There are two places an OpenAI key can go, and they are not the same.**

| Where | Used by | Needed for this project? |
|---|---|---|
| JobSync → Settings → API Keys | JobSync's own in-app AI features | **No** |
| `.env` → `OPENAI_API_KEY` | The ZeroHour Times assessments and research | **Yes** |

If you only want the newspaper, put your key in **`.env`** and leave JobSync's
blank. Putting it in both is harmless but means two places to rotate, and
JobSync encrypts its copy under `ENCRYPTION_KEY` — lose that and its copy is
unrecoverable.

---

## Did it work?

```bash
docker compose logs zerohour-times | tail -20
```

| What you see | Meaning |
|---|---|
| `# queued N posting(s) for matching` | Discovery is working |
| `JOBSYNC_MCP_TOKEN is not set` | Step ③ incomplete, or no restart |
| `HTTP 401` | Token is wrong — re-copy it, or mint a new one |
| `Insufficient scope. Required: jobs:write` | Token missing the scope — mint a new one |
| `Rate limit exceeded` | Normal with a large watchlist; deferred jobs go in next run |

Then open your newspaper: **<http://localhost:8099>**
