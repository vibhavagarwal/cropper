# In-app API key field with OS-keyring storage

Status: ready

## Context

Spec-required (`.scratch/desktop-tool/spec.md`) but never built. `keyring` is already in
`requirements.txt` and unused. Today the only way to configure OpenAI access is the
`OPENAI_API_KEY` environment variable, read implicitly by the `OpenAI()` client constructor
in `src/providers/openai_provider.py:35`. `MainWindow.__init__` (`gui/main_window.py`) wraps
`OpenAICropProvider()` construction in a try/except; on failure `self.provider = None` and
escalation is disabled with a status-bar message. Confirmed via grilling on 2026-09-20.

## Design

- **Entry point**: a "Configure API key..." button inline in the main window (not a menu bar
  — a menu bar was explicitly ruled out as a structural change, out of scope per
  `01-ui-ux-cleanup.md`'s scope boundary). Opens a small dialog.
- **Dialog contents**: enter/edit the key, and a clear affordance to unset it. No test API
  call on save — store directly to the OS keyring via the existing `keyring` dependency. A
  bad key is discovered the same way it is today: the first real escalation call fails with
  whatever error the SDK/API returns.
- **Precedence**: OS keyring is checked first; if empty, fall back to `OPENAI_API_KEY` (today's
  only mechanism keeps working unchanged). The in-app path becomes primary without deprecating
  the env var.
- **Immediate effect**: saving a key re-attempts `self.provider` construction right away — no
  app restart required before escalation becomes available.
- **Clearing**: reverts keyring storage to empty, which falls back to the env var per the
  precedence rule above (not to "no provider" if the env var is still set).
- **Provider scope**: OpenAI-specific only. Additional providers (Anthropic, Grok — spec
  section 5, `src/providers/base.py`'s `CropProvider` ABC) remain explicitly deferred; no
  generic multi-provider key UI needed here.

## Out of scope

- Key validation via a live API call at save time.
- Any UI for providers other than OpenAI.
- A menu bar (or any other structural addition).
