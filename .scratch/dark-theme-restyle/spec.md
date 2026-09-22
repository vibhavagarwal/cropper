# Dark theme restyle (agent-proposed design)

Status: restyle-only thread implemented 2026-09-21 (`gui/main.py`'s `_STYLESHEET_TEMPLATE`,
plus dark-mode chevron icon strokes and new `QTableWidget`/`QHeaderView`/horizontal-scrollbar
selectors for the escalation history dialog). Kept the app's existing selector/property scheme
(`[primary="true"]`/`[quiet="true"]`, `#photoStatus[state=...]`) rather than migrating to the
proposal's `class`-property mechanism, since that would be pure code reorganization with no
visual difference - out of scope for a restyle. The **card-interaction redesign** thread
(collapsing the four action buttons into a `QToolButton` + `QMenu`) remains deferred, not
implemented - see that section below, unchanged.

## Context

User asked a separate agent to make the app look prettier. That agent proposed a full dark
theme (base `#16191d`, panels `#21262d`, accent `#388bfd`, etc. — see the full QSS in the
session transcript) plus a card-interaction restructure (collapsing the four per-card action
buttons into a single button + context menu). User also had the same agent produce a light-mode
variant to compare.

## Decisions (resolved during this conversation, 2026-09-21)

1. **Dark mode over light mode** — light mode "doesn't look that good," confirmed dark is the
   direction.
2. **Keep the status label's current placement** — the user does not like where the proposed
   dark-mode design put the "flagged for escalation" (etc.) status. Today it's a full-width
   `status_label` row directly under the thumbnail, above the keep checkbox (see
   `gui/review_gallery.py`'s `PhotoCard.__init__` layout order: thumb → status → keep →
   escalate checkbox → buttons). The proposed redesign's `badge-warning`/`badge-neutral` classes
   read as small pill tags, which implies moving/shrinking this element - explicitly rejected.
   **Keep the current placement and full-width treatment**, just re-themed with dark colors
   (e.g. `background: #382c0e; color: #e3b341;` for the flagged/warning state, mapped onto the
   existing `#photoStatus[state="flagged"]` selector, not moved elsewhere or restyled as a small
   badge).

## Scope split (recommended, not yet confirmed by the user)

Two separate tickets, since they're different kinds of change:

- **Restyle only**: apply the dark token/QSS system to existing widgets and existing layout
  structure — colors, borders, radii, hover states, the `setProperty("class", ...)` /
  `unpolish`/`polish` pattern replacing the current `setProperty("primary"/"quiet", True)`
  boolean-property pattern. No layout or interaction changes. This is what should absorb the
  "keep status label placement" decision above.
- **Card interaction redesign** (separate, deferred): the proposed collapse of Escalate/Manual
  Crop/Details into a single `QToolButton` + `QMenu`. This is a behavior change, not styling —
  touches `PhotoCard`'s button wiring, the escalate-selection workflow, and the tests added this
  session for `crop_button`/`details_button` (added specifically to support the folder-preview
  "not yet processed" disabled-controls state). Should be scoped and decided on its own, not
  bundled into "make it pretty."

## Issues

- `issues/01-label-chips-and-clipped-empty-state-text.md` — two regressions from the restyle
  itself, found during user verification: mismatched label backgrounds and clipped empty-state
  text. Root causes confirmed by re-reading the code; not yet fixed.
- `issues/02-use-logo-in-empty-gallery-state.md` — use the provided app logo
  (`gui/assets/branding/logo.png`) to fill the empty-gallery state instead of/alongside the
  plain text message.

## Comments
