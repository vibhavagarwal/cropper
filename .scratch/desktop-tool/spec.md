# Desktop tool for the photo pipeline

Status: requirements gathering complete (grilling session, 2026-09-20). Every branch of the
design tree below has been visited and confirmed. Ready to move into planning/implementation
once you give the final go-ahead.

Source material: `photo-pipeline-starter.zip` (the pipeline's own `CLAUDE.md` project brief,
`src/hp5_emulate.py`, `docs/filter_hp5_notes.md`, `docs/reference_stats.json`, tests, tools).
That brief's pipeline order, layout rules, and cost/triage logic are treated as settled
requirements; this document covers what it leaves open — the desktop tool itself.

Note: this repo's own `CLAUDE.md` (agent-skills config) is a different document from the
pipeline brief's `CLAUDE.md` inside the zip. These will need to be reconciled when the pipeline
code is brought into this repo — not yet done.

## Decisions so far

### Scope and build order
- V1 is a thin GUI shell around what's already built in the pipeline (HP5 filter + fixed-canvas
  layout + placeholder center-crop), so something runs today.
- Despite that, **requirements are being captured for the full pipeline lifecycle now**
  (detection, triage, crop escalation, theme routing, portrait filter) even though most of it
  isn't built yet — so later work doesn't require re-deriving requirements.

### Tech stack (verified working together on this machine, 2026-09-20)
- Python 3.14.7 (already installed)
- PySide6 6.11.2 — native desktop GUI, in-process calls into the pipeline code, no IPC layer
- numpy 2.5.3, scipy 1.18.1, Pillow 12.3.0 — existing pipeline test suite (10 tests) passes
  against these versions
- opencv-python 5.0.0 — planned dependency (face/saliency detection), installs clean, not yet used
- Provider SDKs for escalation: see "AI provider" below — not Anthropic-locked

### Distribution
- Local-only, personal tool. Run from source (e.g. `python app.py`). No installer/packaging for v1.

### Filter step
- A filter on/off toggle exists; default is **on**.
- For now, the landscape HP5 filter applies to **all** photos (no theme classifier yet).
- When a portrait filter is designed later, filter selection becomes **automatic per photo**
  based on theme classification, with manual per-photo override always available.

### Processing / review / save model
- Nothing writes to disk automatically. Saving is always an explicit action.
- **Free/local pipeline stages** (EXIF correction, detection, triage decision, formula crop,
  filter, border) run automatically for the **entire input folder** up front, showing results
  progressively in a review gallery as each photo finishes.
- **Paid stages** (escalated AI crop decision) are **never** run automatically across a batch.
  Triggering escalation (per-photo or "escalate all flagged") is an explicit action, and the
  tool shows a **worst-case cost estimate** (assumes every flagged photo needs the stronger/
  pricier tier) before you commit to the spend.
- Review gallery: one entry per photo. You mark which photos to keep.
- Explicit **Save** (or "Save Selected") action writes only the kept photos to disk. Discarded
  results never touch disk.

### Manual crop override
- Interactive crop box: drag/resize directly on the photo, constrained to the shape's locked
  inner ratio (can never produce an invalid crop). Available for any photo, not just the
  "rare human review" escalation-uncertain case.

### Escalation / AI crop decision
- Escalation cost-gating: see "Processing / review / save model" above.
- In the review gallery, an escalated photo shows its **confidence value and which model tier
  answered**, alongside the rendered result — not just the final crop.
- Tier selection (cheap tier first, escalate to stronger tier only on low confidence) is
  **fully automatic** for v1. No manual override setting (e.g. "always cheap" / "always strong").
- v1 uses **immediate/synchronous** escalation calls only. Batch API mode (50% discount,
  confirmed still current per Anthropic's live docs as of 2026-09-20) is a later optimization,
  not built now.

### AI provider
- The escalation call (image + detection metadata in, crop decision + confidence out) is
  **provider-agnostic by design** — built behind a small interface, not hardcoded to one SDK.
  Any vision-capable model with structured/JSON output can implement it (OpenAI, Anthropic,
  possibly xAI Grok).
- **First provider to implement and test against: OpenAI.** The user has OpenAI API billing/
  credits already set up on platform.openai.com; no Claude API subscription yet. (Note: a
  ChatGPT Plus/Pro/Team subscription does NOT include API access — API billing is separate.
  Confirmed the user already has API credits, not just a ChatGPT subscription.)
- Anthropic (the starter project's originally-planned dependency) and other providers become
  swappable implementations behind the same interface, added later.

### API key handling
- Default: read from environment variable (matches each provider SDK's own convention).
- Optional override: in-app settings field, stored via OS-level secure storage (e.g. `keyring`
  on Windows Credential Manager), never written to a plaintext config file.

### Cost / decision tracking
- Visible in-app: a running cost total and a history list of per-photo decisions (escalated or
  not, which model/tier handled it, cost), not just a background log file. Satisfies the
  pipeline brief's open item #7 (per-photo decision log for tuning triage thresholds).

### Triage thresholds
- Follow the same convention the filter code already uses: a config value edited directly
  (code or config file) as thresholds get tuned against real batches. **No in-app settings UI**
  for this — it's infrequent, data-driven tuning, not a live knob.

### Input
- Folder picker as the primary path (matches the CLI's existing folder/glob workflow), plus
  drag-and-drop of a folder onto the window as a convenience. Both land on the same input list.
- No individual multi-file picker for v1 — the tool's premise is batch folders; cherry-picking
  is what the review gallery's keep/discard already covers.

### Output
- Default: fixed convention, a `<input-folder>/out/` subfolder (matches the CLI's own `-o
  hp5_out` default). Optional override via a folder picker to redirect a specific run.

### Error handling
- Skip-and-continue: a single failed photo (corrupt file, unreadable EXIF, an escalation call
  erroring out) is flagged in the review gallery with its error reason; the rest of the batch
  keeps processing. No abort-on-first-failure behavior.

### Detection pass transparency
- Not shown by default in the main review gallery grid (keeps the common case clean).
- Available in a per-photo detail view: detected face box, saliency heatmap, symmetry score —
  whatever drove that photo's triage decision. Directly supports the triage-threshold tuning
  workflow already planned (turns "this crop is wrong" into "the threshold needs adjusting").

### Settings persistence
- Remembers last-used settings (shape, canvas size, filter toggle, last input/output folders)
  across app restarts, via a small local config file (e.g. JSON in a user config directory).

### Shape per run
- One shape applies to the whole folder per run (no per-photo shape mixing in a single pass).
  Re-running the tool over the same folder with a different shape setting is the escape hatch
  for wanting more than one shape — cheap to do since nothing auto-saves.

### Border (inherited from the pipeline brief, not re-litigated here)
- The doc calls border a "Locked decision": white, uniform, 2% of canvas long edge, always
  applied after the filter. Not exposed as a desktop-tool setting — stays fixed, matching the
  brief's own locked framing rather than the CLI's undocumented `--border` override escape hatch.

### Portrait theme filter
- Explicitly deferred. The user will define the portrait filter's look later; until then,
  portrait/ambiguous-theme photos are flagged rather than silently given the landscape filter
  (see "Filter step" above).

## Open items

None outstanding — every branch below has been visited. Ready for the next phase (planning /
implementation) pending final confirmation.
