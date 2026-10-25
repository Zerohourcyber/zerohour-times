# Publishing this repository

Notes for the maintainer. Delete this file before making the repo public, or
keep it — it harms nothing.

## What a user actually does

Worth being clear, because testing this project on a remote server made it look
harder than it is. A normal user runs everything on their own computer:

```bash
git clone https://github.com/Zerohourcyber/zerohour-times.git
cd zerohour-times
./scripts/setup.sh
docker compose up -d
```

Then <http://localhost:3737> and <http://localhost:8099>. No server, no VPN, no
tunnel, no port forwarding, no domain, no TLS certificate. Both ports bind to
`127.0.0.1`, which on their own machine is simply their browser.

Windows and macOS users need Docker Desktop. Linux users need Docker Engine.
That is the whole dependency list — the application itself has none.

## Publishing, step by step

### 1. Finish the blocking items

See [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md). Screenshot, `Zerohourcyber`
replacement, live integration test, smoke test, LICENSE name.

### 2. Create the repository on GitHub

Go to <https://github.com/new>:

- **Name:** `zerohour-times`
- **Visibility:** **Private** to begin with. Flip to public once you have
  cloned it fresh and confirmed it works — see step 4.
- **Do not** tick "Add a README", "Add .gitignore" or "Choose a licence".
  This repository already has all three, and letting GitHub create them
  produces a conflicting first commit.

### 3. Push

```bash
cd /path/to/zerohour-times
git remote add origin git@github.com:Zerohourcyber/zerohour-times.git
git push -u origin main
```

Use SSH (`git@github.com:`) rather than HTTPS if you have a key; otherwise
HTTPS with a personal access token works the same.

### 4. Prove it from a stranger's point of view

This is the step that catches what local testing cannot:

```bash
cd /tmp
git clone git@github.com:Zerohourcyber/zerohour-times.git fresh-test
cd fresh-test
./scripts/setup.sh
docker compose -p fresh-test up -d
```

If anything is missing from the repository — a file you had locally but never
committed — it fails here rather than in front of a stranger. Then:

```bash
docker compose -p fresh-test down -v && cd .. && rm -rf fresh-test
```

### 5. Make it public

Settings → General → Danger Zone → Change visibility.

Then, still in Settings:

- **Features:** turn off Wikis and Projects unless you want them. Leave Issues on.
- **Security → Private vulnerability reporting:** enable it. `SECURITY.md`
  tells people to use it.
- **Actions:** confirm the CI workflow ran and is green.
- **About** (top right of the repo page): add a one-line description and topics
  such as `job-search`, `ai`, `responsible-ai`, `docker`, `self-hosted`,
  `ai-governance`.

### 6. Credit upstream

Star [Gsync/jobsync](https://github.com/Gsync/jobsync). Consider opening an
issue there saying you have built on it — maintainers generally like knowing,
and a link from an established project is worth more than any amount of SEO.

## If you want people to find it

The thing that distinguishes this project is not that it calls an AI — everyone
does. It is [docs/AI-GOVERNANCE.md](docs/AI-GOVERNANCE.md): a documented record
of how the system was evaluated, the failures that evaluation caught, and what
remains unmeasured. Lead with that rather than the feature list.

## Keeping your own instance separate

Your production deployment stays where it is. The public repository is the code;
your `.env`, `profile.md` and `config.json` are not in it and never will be —
they are gitignored. If you later want your instance to run the public code,
clone it somewhere and copy those three files across.
