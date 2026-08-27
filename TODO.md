# TODO — next session

Written 2026-08-16, after the audit fix round (`f7c1de5`). Everything here is
buildable without waiting on CMID. Items needing a client decision are tracked
separately in `AUDIT_FINDINGS.md` and the `CLAUDE.md` status log, not here.

Before starting: `bench start` (redis 13000/11000 must be up or one schedule
test fails on `global_search` and reads like a code fault). Never a bare
`bench migrate` for Workspace/Page/Report changes — it and `reload_doc` have
both deleted workspace JSON from disk. Confirm 9 files survive with
`ls bandhu_app/bandhu_app/workspace | wc -l`.

---

## Build

### 1. The eight reports — 3 of 8 done (2026-08-20)
Built: **Session** (row per camp), **Tests** (row per test, with the patient's
sex / age group / native state), **Clinic** (aggregate by clinic, project, unit,
LSG or site). All three are Script Reports with a summary band, a chart and a
Dashboard shortcut; shared per-camp counts live in `utils/clinic_stats.py`.

Left: Medicine Utilisation, Patient History, Treatment, Referral, PHI. Two of
those are blocked on data that does not exist yet — Referral (no code creates a
`Referral` doc; see item 2) and Medicine Utilisation beyond per-camp counts (no
stock ledger; see the CLAUDE.md status log). Patient History and Treatment are
buildable now and should follow the Tests Report's row-per-record shape.

Watch: a Script Report runs raw SQL and **bypasses permissions entirely**. The
`roles` table on the Report record is the only gate — Session Report is System
Manager only. Decide who may run each one before writing the SQL, not after.

`age_group()` in `utils/patient.py` uses bands we picked (0-14, 15-29, 30-44,
45-59, 60+) because the scope doc never defines them. Get CMID to confirm before
more reports bake them in.

### 2. Helpline UI and the follow-up-due list
`doctype/referral/` and `doctype/referral_followup/` already hold the right
fields (`reason`, `notes`, `priority`, `status`, `helpline_flag`,
`required_action_from`). What does not exist anywhere: a page, a report, or a
notification producing a "due today" list. `notification/` is absent too.

First decision to make (ours, not the client's): dedicated page in the
CAD/Doctor/Nurse pattern, or the standard Desk list plus a report. The scope
doc asks for a "pop-up due list", which argues for a page.

### 3. Programme follow-up due list (PF1–PF3)
Same gap, same mechanism as #2. Build after it and reuse whatever #2 lands on.

### 4. Clinic day summary
Steps 17 and 21–22 of the scope flow. Nothing generates an end-of-day summary
today. Sharing it over WhatsApp is a separate, blocked item — build the
summary itself first, it stands alone as a print format or report.

### 5. Seed the real site masters
29 sites and 25 locations from the client's "Weekly site list 8 June 2026"
spreadsheet. Note `Perumbavoor` spans two LSGs, so Location alone is not a key.

The LSG *numbering* for the 18 real LSGs still needs CMID — only 3 codes exist
today. Seed the sites and locations now regardless; the numbering can follow.
This gets harder the longer it waits, because the LSG code is permanent and
printed on every patient card already issued.

---

## Smaller, still open

### 6. Doctor double-booked in one day
`find_active_session` (`utils/session.py`) breaks ties on `creation desc`,
i.e. arbitrarily. A doctor scheduled to a morning and an evening camp sees one
of them, at random, with no way to switch — patients at the other are
invisible. Needs a camp switcher on the board, not just a query change.

### 7. `regenerate_future_sessions` drops beyond-horizon camps
`bandhu_session_schedule.py:171-198` deletes every future `Planned` session
without encounters at any date, then regenerates only to `today + horizon_days`
(default 56). Anything dated past the horizon disappears from staff schedules
until the rolling horizon reaches it again.

### 8. `Patient Queue` has no referential integrity
`clinic_session` and `patient` are `Data`, not `Link`, so deleting an encounter
or a session leaves dangling rows, and `sync_to_queue` only ever flips `status`
to Done — it never removes a row. `created_on` / `last_updated` are typed
`Autocomplete`, which is wrong for timestamps and looks odd on the Desk form.

Related and bigger: the queue keys on `patient` alone, which has a unique
index, so the same patient in two camps on one day silently moves between
boards. The crash path is fixed; this behaviour is not.

### 9. Framework / Quality desk icons missing for System Manager
Unintended fallout from the workspace visibility scoping. `Marley Health` still
shows correctly, so it looks specific to `parent_icon` nesting on those two
rather than to the roles restriction. Administrator can still reach
`/app/build` and `/app/quality` directly, so this is cosmetic.

### 10. `/undefined` 404 on the Desk landing page
Pre-existing, source not traced.
