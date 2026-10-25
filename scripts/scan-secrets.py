#!/usr/bin/env python3
"""Fail if anything that looks like a credential or personal datum is tracked.

Run locally before committing, and in CI on every push. It errs toward false
positives: a scanner that never complains is a scanner nobody checks.
"""
import re, subprocess, sys

PATTERNS = [
    ("OpenAI key",        r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    ("Anthropic key",     r"sk-ant-[A-Za-z0-9_-]{20,}"),
    ("GitHub token",      r"gh[pousr]_[A-Za-z0-9]{20,}"),
    ("Slack token",       r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    ("AWS key id",        r"AKIA[0-9A-Z]{16}"),
    ("Bearer token",      r"[Bb]earer\s+[A-Za-z0-9._-]{20,}"),
    ("MCP token",         r"\b(?:jsync_|jbs_)[A-Za-z0-9_-]{16,}"),
    ("64-hex secret",     r"\b[0-9a-f]{64}\b"),
    ("id|hex64 PAT",      r"\b\d+\|[0-9a-f]{64}\b"),
    ("Private RFC1918 IP", r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
    ("Tailscale CGNAT IP", r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"),
    ("Private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
# Files allowed to contain pattern-shaped text because they are documentation
# of the patterns themselves.
ALLOW = {"scripts/scan-secrets.py", ".github/workflows/ci.yml"}


def main():
    try:
        files = subprocess.check_output(["git", "ls-files"], text=True).split()
    except subprocess.CalledProcessError:
        print("not a git repository", file=sys.stderr)
        return 2
    findings = []
    for path in files:
        if path in ALLOW:
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    for name, pat in PATTERNS:
                        m = re.search(pat, line)
                        if m:
                            findings.append((path, n, name, m.group(0)[:28]))
        except OSError:
            continue
    # Files that must never be tracked at all.
    never = {"profile.md", "config.json", ".env"}
    for path in files:
        if path.split("/")[-1] in never:
            findings.append((path, 0, "private file tracked", path))

    if findings:
        print(f"SECRET SCAN FAILED — {len(findings)} finding(s):\n")
        for path, n, name, snippet in findings:
            print(f"  {path}:{n}  {name}: {snippet}")
        print("\nNothing is published until this is clean.")
        return 1
    print(f"secret scan clean — {len(files)} tracked files, 0 findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
