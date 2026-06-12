# Security Policy — MATRIX

## Credential exposure notice (2026-06-10)

A developer-local `app/.env` was found holding **real credentials**: a Google AI Studio
`GOOGLE_API_KEY`, a Mapbox public token, a `VERCEL_TOKEN`, and a `FLY_API_TOKEN`.

**Verified status (2026-06-10):** `app/.env` is *not* tracked by git and none of those
secret values appear anywhere in the repository's history — verified with
`git ls-files app/.env` (empty), `git log --all -- app/.env` (empty), and
`git log --all -S "<each secret value>"` (no hits on any branch). Nothing was pushed.

**Action required regardless: rotate the keys.** The `.env` contents have circulated
outside the repo (developer tooling and AI-agent sessions read the file), so treat them
as potentially exposed:

1. **`GOOGLE_API_KEY`** — revoke and re-issue in [Google AI Studio](https://aistudio.google.com/apikey).
2. **`VERCEL_TOKEN`** — revoke under Vercel → Account Settings → Tokens; re-issue with the narrowest scope.
3. **`FLY_API_TOKEN`** — revoke with `fly tokens list` / `fly tokens revoke`; prefer app-scoped deploy tokens.
4. **`NEXT_PUBLIC_MAPBOX_TOKEN`** — public-scope by design, but rotate and add URL restrictions in the Mapbox dashboard.

A standing rule for this repo: **removing a file from the git index does not purge it
from history.** If a secret is ever actually committed, deleting the file or rewriting
the working tree is not enough — the value remains retrievable from history and from any
clone/fork. The only safe response is to rotate the secret immediately (and optionally
rewrite history with `git filter-repo`, which still does not un-leak anything already cloned).

## Secrets-handling policy

- **Never commit secrets.** `.gitignore` blocks `.env` at every depth, plus
  `credentials.json`, `token.json`, and `*.key`. `app/.env.example` (placeholders only)
  is the documented template — copy to `app/.env` and fill locally.
- **Production secrets live in the platform, not in files:**
  - Fly.io (API): `fly secrets set GOOGLE_API_KEY=...` — never in `fly.toml` (its `[env]`
    block is for non-secret config only).
  - Vercel (web): Project → Settings → Environment Variables.
  - GitHub Actions: repository **Actions secrets**, referenced as `${{ secrets.* }}`.
    The current CI (`.github/workflows/ci.yml`) intentionally requires no secrets.
- **Keys carry the narrowest scope and shortest life practical.** Prefer app-scoped
  deploy tokens over account-wide tokens.
- **Data privacy:** Iloilo pilot data handling is governed by RA 10173 (Philippine Data
  Privacy Act) — see `docs/clr-matrix.md` for the compliance register.

## Reporting a vulnerability

Report suspected vulnerabilities or exposed credentials privately to
**carlosjericodelatorre@gmail.com** (repository maintainer) — do not open a public issue.
You should receive an acknowledgement within 72 hours. Please include reproduction steps
and, for credential exposure, where the value was observed.
