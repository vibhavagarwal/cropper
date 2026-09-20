## Session scope

- A session does the work it was given — implementing scoped tickets/bug fixes, or capturing
  new issues/specs (via the issue tracker below) — and stops there. Don't roll on into new,
  unscoped development in the same session once that work is done, even when a natural next
  step is obvious (e.g. starting to implement a spec you just wrote up).
- New feature development starts in a fresh session. If a session's own work surfaces a new
  feature or a design worth building, write it up (spec + issue tickets) and hand it off —
  don't start implementing it there.
- Keep test runs scoped to verifying the current change. Don't run the full suite or repeated
  dev-loop iterations beyond what's needed to confirm the task at hand without checking in
  first — the user is actively conserving tokens and finds unrequested extra runs costly and
  annoying.

## Agent skills

### Issue tracker

Issues and specs live as markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
