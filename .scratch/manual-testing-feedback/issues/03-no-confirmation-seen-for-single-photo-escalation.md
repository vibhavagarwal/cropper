# No confirmation dialog seen when escalating a single photo, and no success message either

Status: diagnosed further — user confirmed the escalation did run (so the "no API key"
hypothesis below is ruled out), and confirmed via a side-by-side comparison that batch
escalation ("Escalate selected") shows both the confirmation dialog and a success message
correctly. One part of this (no success message) is now a **confirmed code gap**, not a
hypothesis. The other part (no confirmation popup) remains unconfirmed. Not fixed.

## Update: user follow-up testing

> Yes, the escalation did happen. But I got no popup asking me to go ahead, and no success
> message as well. I tested the bulk escalation and messages showed up fine.

This rules out the `self.provider is None` hypothesis below — escalation only runs at all past
the `if self.provider is None: return` guard in `_on_escalate_requested`, so the provider was
configured. It also gives a clean comparison: the batch path (`_on_escalate_selected_clicked`)
and the single-photo path (`_on_escalate_requested`) both construct the same
`EscalationConfirmDialog` class the same way, but only the batch path explicitly shows a
post-completion message. Re-reading `gui/main_window.py` with this comparison in mind:

**Confirmed gap — no success message for single-photo escalation:**
`_on_escalate_selected_clicked` (`gui/main_window.py:214-240`) explicitly builds a summary
string and shows it via both `self.statusBar().showMessage(...)` and a `QMessageBox` (warning
or information, depending on outcome). `_on_escalation_done` (`gui/main_window.py:198-212`),
which is what actually runs on completion for **both** the single-photo and batch paths, does
neither — it only updates the card's in-place status text (`self.gallery.update_job(job)`) and
the gallery's running-cost header (`self.gallery.refresh_cost()`). The batch path's visible
"Escalated N of M" messaging is bolted on separately, only in
`_on_escalate_selected_clicked`, after all the individual `_run_escalation_worker` calls finish
— nothing equivalent exists in `_on_escalate_requested` for the single-photo case. This is a
genuine, code-confirmed asymmetry: single-photo escalation was simply never given a completion
message, not a rendering glitch or a missed toast.

**Still unconfirmed — no confirmation popup for single-photo escalation:**
`_on_escalate_requested` and `_on_escalate_selected_clicked` both call
`EscalationConfirmDialog(self.provider, num_photos=..., parent=self).exec()` the same way — a
plain modal `QDialog.exec()`, no code-visible difference between the two call sites that would
explain one showing and the other not. Since escalation for the single photo definitely
happened, either `confirm.confirmed()` returned `True` without the user consciously interacting
with it, or the dialog appeared and was missed (e.g. opened without stealing focus, appeared
behind the main window, or was dismissed by a stray keypress/click). No code defect has been
found for this half yet — it may be a focus/z-order issue rather than a logic bug, which won't
show up from reading the dialog code alone.

## Observed

User escalated a single photo (per-card "Escalate" button, not "Escalate selected"). No
confirmation dialog was seen beforehand, and no success message was seen afterward. Batch
escalation via "Escalate selected" was tested separately and both the confirmation dialog and
completion message showed up correctly.

## Ruled out

`self.provider is None` (no API key configured) — this would have prevented escalation from
running at all (`_on_escalate_requested` returns immediately in that case), but the user
confirmed the escalation did happen. So the provider was configured; this is not an API-key
issue.

## Notes for whoever picks this up

- **No success message (single-photo)**: fix shape is straightforward — give
  `_on_escalate_requested`'s completion path the same kind of visible confirmation
  `_on_escalate_selected_clicked` already has (status bar + `QMessageBox`), rather than relying
  on `_on_escalation_done`'s silent card/cost-header updates alone. Should be testable directly:
  assert a status bar message (or equivalent) appears after single-photo escalation completes,
  the same way batch escalation is presumably tested.
- **No confirmation popup (single-photo)**: no code defect found — the single-photo and batch
  call sites construct and `.exec()` the same `EscalationConfirmDialog` the same way. Needs a
  live repro to investigate further (does it reproduce reliably? does the main window have
  focus at the time? does it happen only right after some other dialog closes?) — this may turn
  out to be a Qt focus/z-order issue rather than a logic bug, which reading the code alone won't
  surface.

## Session update: fix applied, other half still unconfirmed

**No success message (single-photo) — fixed.** `_on_escalate_requested` in `gui/main_window.py`
now shows a status bar message and a `QMessageBox.information` (or `.warning` on failure) after
the escalation worker completes, giving it the same visible completion messaging
`_on_escalate_selected_clicked` already has, including the filename. The existing regression
test `tests/test_gui_smoke.py::MainWindowWiringTests::test_escalate_single_photo_shows_success_message`
now passes (confirmed green, along with the rest of `MainWindowWiringTests`, 35/35 passing).

**No confirmation popup (single-photo) — still unconfirmed, not attempted.** This session had no
way to drive the actual running GUI (no interactive display/live app available in this
environment, only the offscreen-Qt automated test suite) — automated tests can't observe a
missed-focus/z-order symptom, only whether `.exec()`/`confirmed()` were called, which they
already were shown to be identical between the two call sites. No new code defect was found in
`_on_escalate_requested` vs. `_on_escalate_selected_clicked` beyond what the diagnosis above
already documents; both still construct and `.exec()` `EscalationConfirmDialog` identically. This
half is left as-is per the explicit instruction not to guess at a fix for something that might not
be broken — it needs a live repro in the actual running app by someone who can interact with it.

## Comments
