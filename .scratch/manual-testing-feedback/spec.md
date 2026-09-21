# Manual testing feedback: bw-grain-filter follow-up

Status: diagnosed 2026-09-20 (code-inspection only, nothing reproduced live, nothing fixed) —
see `## Handoff for next session` below.

## Context

The user manually tested the running app after the three `bw-grain-filter` tickets landed
(B/W filter split into independent B/W + grain controls, `.scratch/bw-grain-filter/`). Four
issues surfaced during that session, captured as tickets here, then diagnosed by reading code
(no fixes applied — diagnosis and handoff-writing only, per explicit instruction not to code
this session).

## Issues

- `issues/01-bw-off-still-saves-black-and-white.md` — **root cause confirmed**:
  `gui/save_action.py:19` force-converts every saved photo to `"L"` (grayscale) mode regardless
  of `job.apply_bw`, a leftover from before the B/W/color split. Highest-confidence diagnosis of
  the four; also the clearest regression from the `bw-grain-filter` work itself.
- `issues/02-output-folder-default-and-save-confirmation-unclear.md` — not a bug, a feature
  gap, with a two-part **required** acceptance criteria (user's own wording, see the issue
  file's "Requirement" section — both parts required, not optional extras): (1) the UI must
  show the default output folder (`<input folder>/out` today) before Save, explicitly labeled
  as the default; (2) after Save, a durable prompt — not the current transient status-bar
  message — stating the number of files saved and where. Pre-existing, unrelated to
  `bw-grain-filter`.
- `issues/03-no-confirmation-seen-for-single-photo-escalation.md` — two-part issue, one part
  now **confirmed**: single-photo escalation has no completion message at all in
  `_on_escalation_done` (`gui/main_window.py`), unlike batch escalation which explicitly builds
  and shows one — a real, code-confirmed asymmetry. The other part (no confirmation dialog
  beforehand) has no code defect found — single-photo and batch both `.exec()` the same dialog
  class the same way — so it needs a live repro to investigate further, possibly a Qt
  focus/z-order issue rather than a logic bug. The earlier "no API key configured" hypothesis
  is ruled out (the user confirmed escalation did run). Pre-existing, unrelated to
  `bw-grain-filter`.
- `issues/04-escalated-photo-appears-squeezed-not-cropped.md` — **confirmed gap, unproven as
  root cause**: `apply_escalation` (`src/pipeline.py`) trusts the AI provider's returned crop
  box without validating it matches `inner_ratio`, unlike the formula-crop path which is
  guaranteed on-ratio by construction. Confirmed this is **not** a `bw-grain-filter` regression
  (that work never touched crop/resize geometry). Pre-existing gap, surfaced by manual testing
  now.

## Handoff for next session

**Priority order suggested:** 01 (highest confidence, clear fix shape, likely most impactful —
color output is the headline feature of the just-shipped work and it's currently broken at
save time) → 04 (confirmed gap, real risk of visibly wrong output) → 03 (needs the API-key
question answered before scoping) → 02 (UX improvement, not a correctness bug, lowest urgency).

Each issue file has a "Likely fix shape" or equivalent section with a concrete starting point,
plus what test coverage is missing (all three real bugs — 01, 03, 04 — got through the
existing/new test suites because of specific, named coverage gaps, not random luck; each issue
file names the gap). Follow this repo's TDD convention: a new failing test per fix before
touching the fix itself, same as the `bw-grain-filter` tickets did.

None of the four have been reproduced live in the running app by the diagnosing session — only
read and reasoned about from source. Confirm each diagnosis with a real repro (or a new test
that fails for the hypothesized reason) before trusting it as the actual root cause,
particularly 03 and 04 where the notes above are explicit about what's unconfirmed.

## Separate, unrelated thread from this same session: UI/UX design review

Not a bug list — the user also had a design pass done externally (a "Claude Design" session,
prompted using the earlier prompt in this conversation) and asked for it to be reviewed. That
review was conversational (see chat), not written to a ticket, since it's mockup feedback
rather than an implementation-ready spec. Summary for context if a future session needs it:
the deliverable (`Cropper UI Pass.html`, rendered via a local preview since it's a bundled
export, not plain static HTML) is a genuinely usable QSS-based redesign — real Qt QSS syntax,
a token/contrast spec, before/after comparisons, 3 layout options for the new B/W+grain row
(with the structural one explicitly marked "needs approval," respecting the original "cosmetic
only" scope constraint), and an explicit itemized list of the minimal Qt code touches (object
names, properties, a few `setWordWrap`/`setMinimumWidth` calls) the stylesheet depends on to
bind correctly.

## Running both tracks as one orchestrating session with two parallel agents

Revised plan (per the user, superseding the "two separate sessions" framing below): a single
new session reads this handoff, then spawns two agents in parallel via the Agent tool, each
with `isolation: "worktree"` so they work on isolated git worktrees and can't step on each
other's uncommitted changes — this removes the live-editing conflict risk entirely; the only
remaining coordination point is merging both branches back afterward. Concretely, that session
should:

1. Read this file and all four issue files in full.
2. Call the Agent tool **twice in one message** (so they run in parallel, per the Agent tool's
   own guidance on independent calls) — once with the "Bug-fix session prompt" below and once
   with the "UI/QSS session prompt" below, both with `isolation: "worktree"`.
3. Wait for both to complete (they run in the background; the session gets notified).
4. Merge the bug-fix branch to `master` first — it's the smaller, more surgical change.
5. Merge/rebase the UI/QSS branch on top of that, and resolve the overlap in
   `gui/main_window.py` (and possibly `gui/input_panel.py`) by hand — see the file-ownership
   table below for exactly which lines/methods belong to which track, so the merge is
   mechanical rather than a re-review of either agent's work.

The file-ownership table and both prompts below are written to be handed to the Agent tool
directly (self-contained, no assumed conversation context) — that still holds under this
revised plan.

**Why not spawn them right now, in this session:** this session's job was diagnosis and
handoff-writing, not implementation — per this repo's own session-scope convention
(`CLAUDE.md`), new implementation work starts in a fresh session rather than rolling on from
here. The next session is where the two agents actually get spawned.

**File ownership by track:**

| File | Bug-fix track | UI/QSS track |
|---|---|---|
| `gui/save_action.py` | fixes issue 01 | — |
| `src/pipeline.py` | fixes issue 04 (`apply_escalation`) | — |
| `gui/escalation_dialog.py` | — | `cost_label.setWordWrap`/`setMinimumWidth` |
| `gui/review_gallery.py` | — | object names, `_update_empty_state`, grid alignment |
| `main.py` | — | stylesheet string + `{A}` asset substitution |
| new SVG assets | — | 3 required icons, 7 optional (needs separate approval) |
| `gui/main_window.py` | **overlap** — issues 02 & 03 fixes live here (`_on_save_clicked`, `_on_escalate_requested`, `_on_escalation_done`) | **overlap** — `setProperty("primary"/"quiet", ...)` on buttons, `bottom_row.insertStretch(3)` |
| `gui/input_panel.py` | **possible overlap** — issue 02 may want the default folder shown here | **overlap** — `settings_row` spacing, `grain_checkbox.toggled` wiring (needs approval) |

**Merge order once both agents finish:** merge the bug-fix branch first — it's the smaller,
more surgical change (4 tickets, mostly logic, minimal layout churn) — then merge/rebase the
UI/QSS branch on top and resolve the overlap in `gui/main_window.py` / `gui/input_panel.py` by
hand. The table above shows it should be a small, mechanical merge (different methods/lines in
the same file in practice — bug fixes touch `_on_save_clicked`/`_on_escalate_requested`/
`_on_escalation_done`, the QSS touches touch `setProperty` calls and layout spacing), not a
re-review of either agent's actual work.

**Scope boundary for the UI/QSS session:** cosmetic/QSS + the itemized minimal code touches the
stylesheet depends on (object names, properties, `setWordWrap`, etc.) only. The one item in the
mockup marked "needs approval" — moving `Process Folder` into the settings group box with a
divider widget (layout option C), and `grain_checkbox.toggled -> grain_size_combo.setEnabled`
— should be flagged to the user for a yes/no before implementing, not built by default.

## Prompts for the two next-session agents

**Bug-fix session prompt:**

> Read `.scratch/manual-testing-feedback/spec.md` and all four files under
> `.scratch/manual-testing-feedback/issues/` in full before starting. Each issue has a
> diagnosis (root cause or narrowed hypothesis) from code inspection, done in a prior session —
> nothing has been fixed yet, and none of the four have been reproduced live, only reasoned
> about from source. Follow this repo's TDD convention (see `superpowers:test-driven-development`
> and how `.scratch/bw-grain-filter/` was implemented): write a failing test that captures the
> bug before touching the fix, for each of the four issues. Work through them in the priority
> order given in `spec.md` (01 → 04 → 03 → 02), fully finishing and verifying each before
> starting the next. For issue 03, confirm live in the running app whether the confirmation
> dialog issue reproduces before assuming a fix is even needed — it may be a one-off focus
> issue, not a logic bug. Run the affected test files after each fix (not the full suite
> repeatedly — this repo's full-suite run can intermittently stall; split into per-file runs if
> so, per `CLAUDE.md`). Stop and ask if a fix's scope is ambiguous rather than guessing.

**UI/QSS session prompt:**

> A UI/UX design pass for this app was done externally and reviewed in a prior session — see
> `.scratch/manual-testing-feedback/spec.md`, section "Separate, unrelated thread from this
> same session: UI/UX design review" for the summary, and ask the user for the
> `Cropper UI Pass.html` file (a bundled export — open it by serving it with a local HTTP
> server and loading it in a browser, not by reading the HTML source directly, since it bundles
> its sections as iframes). Implement the QSS stylesheet from its "Draft QSS and code touches"
> section into `main.py`'s `_STYLESHEET`, plus the itemized minimal code touches it lists in
> `gui/review_gallery.py`, `gui/main_window.py`, `gui/input_panel.py`, and
> `gui/escalation_dialog.py` (object names, `setProperty` calls, `setWordWrap`, etc. — nothing
> beyond what's listed). You'll need the 3 required SVG icons (chevron-down, chevron-up, check)
> it references; the other 7 icons and the "Process Folder inside the settings group + divider"
> layout option are both explicitly marked "needs approval" in the mockup — ask the user
> before building either rather than including them by default. Scope is cosmetic/QSS only, no
> other structural or behavioral changes. Note: `gui/main_window.py` and `gui/input_panel.py`
> may have changed since the mockup was reviewed if a separate bug-fix session ran first (see
> the same spec.md section for the coordination plan) — diff against current `master` rather
> than assuming the mockup's line numbers/context still match exactly.
