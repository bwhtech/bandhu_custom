# bandhu_app — Read-Only Security & Correctness Audit

Scope: `bandhu_app`, mobile-clinic MIS. (Header as originally written said
"Frappe v15, site `bandhuapp.local`" — both were wrong: this bench runs
frappe **17.x-develop**, and the live site is **`bandhu-int.localhost`**.)
Method: static review of the app module only. No `bench migrate`/`reload_doc`,
no DB access, no live HTTP execution (the audit is read-only by rule). Every
finding cites `file:line`; nothing below is inferred beyond what the code says.

Severity key: **HIGH** = exploitable without special circumstances;
**MEDIUM** = exploitable, but needs a precondition (concurrency, a low-priv
user, a specific action); **LOW** = integrity/operational gap; **INFO** =
reported because the brief asked, not because it is a defect.

---

## Findings (sorted HIGH → LOW)

### F1. HIGH — Stored XSS in the patient card print template

**STATUS 2026-08-26: FIXED.** `| e` on `patient_name`, `mobile`, `grouped_clinic_id` and PR #18's new `custom_abha_id`; the `src`/`alt` attribute interpolations in the QR `<img>` escaped later the same day (`f5266e9`) after a live render showed them still raw. Verified by rendering the real template with `<img src=x onerror=alert(1)>` as the name.

`print_format/bandhu_patient_card/bandhu_patient_card.json` renders
`{{ doc.patient_name or "" }}` and `{{ doc.mobile }}` with **no Jinja escape
filter**. Frappe's Jinja environment has autoescape off by default
(`frappe/utils/jinja.py:56` — `SandboxedEnvironment(loader=..., undefined=...,
cache_size=32)`, no `autoescape=True`), so `patient_name` is emitted as raw
HTML.

How it fires:
1. `register_patient` (cad_form.py:169-174) stores `full_name` as free text
   into `Patient.patient_name` — no HTML filtering, only "required" + length.
   Any CAD (the lowest-privilege field role) can submit
   `full_name = '<img src=x onerror=...>'`.
2. Whenever any staff prints that patient's card,
   `get_patient_card_html` (cad_form.py:107-135) returns the rendered card,
   and the frontend writes it into a **same-origin** document:
   `cad_form.js:214-220` `window.open("", "_blank")` + `document.write(card_html)`
   (an `about:blank` document inherits the opener's origin).
3. The payload executes in that origin with the *printer's* session context
   (doctor, nurse, or System Manager — all strictly more privileged than the
   CAD who planted it), enabling session-cookie theft / authenticated API
   calls as the printer.

Note: `{{ doc.sex }}` is escaped via `_(doc.sex)` and `dob` via
`frappe.utils.formatdate`; `custom_bandhu_id` is machine-generated digits.
`patient_name` is the reachable vector.

Fix: `{{ doc.patient_name | e }}`, `{{ doc.mobile | e }}` (and any future
dynamic value in the template).

### F2. MEDIUM — Encounter workflow transition is TOCTOU; no lock, last-write-wins

**STATUS 2026-08-26: NOT A DEFECT — closed.** Guarded twice, now proven by execution rather than by reading: `Document.check_if_latest` (`frappe/model/document.py:1404`) raises `TimestampMismatchError` on every `doc.save()`, and underneath it `validate_workflow_state` re-reads the DB via `get_doc_before_save()` and refuses the illegal jump. Neutralising the framework check makes the covering test go red on the app's own guard. Regression test: `test_encounter_concurrency.py`.

`validate_workflow_state` (utils/patient_encounter.py:29-58) is the only guard
on `custom_workflow_state`. It does: read `old_state` via `get_doc_before_save`,
compare against `ALLOWED_TRANSITIONS`, throw if illegal. There is no `FOR
UPDATE`, no version column, no conditional UPDATE, no
`frappe.client.save`-style timestamp check anywhere in the transition path.

Consequence: two concurrent saves of the same encounter both read the same
`old_state`, both pass validation, and the last commit wins. Concrete failure
(cad_form/doctor_form page methods): two `order_test` calls racing
(doctor_form.py:168-192) both pass the `"Waiting for Doctor"` gate
(doctor_form.py:179) and both `doc.save()`; each loaded the child table before
the other committed, so the second save **silently drops the first request's
test rows** and the surviving `custom_workflow_state` is whichever request
committed last. Same pattern in `complete_encounter`/`prescribe_medicine`
(doctor_form.py:235-258, 195-232), `submit_test_results`/`dispense_medicine`
(nurse_form.py:158-205).

The client already mitigates same-tab double-click (dialog `.hide()` + screen
freeze) and this exact race has bit once in production
(`QueryDeadlockError` from a double-fired `advance_patient`, status log
2026-08-10). The backend remains the layer with no defense; two devices or a
network retry still race. Guard: compare-and-swap on save
(`frappe.db.sql("UPDATE ... WHERE custom_workflow_state=%s")` or a
conditional UPDATE), or lock the row (`FOR UPDATE`) before the read.

### F3. MEDIUM — `sync_to_queue` keys the queue on `patient` only → cross-session overwrite and a duplicate-insert race

**STATUS 2026-08-26: FIXED, after a first fix that never worked.** The 2026-08-15 fix caught `frappe.DuplicateEntryError`, which is raised only for a **primary-key** collision (`base_document.py:837`); `Patient Queue.patient` is a unique **field**, whose violation raises `frappe.UniqueValidationError` (`base_document.py:917`) — an unrelated branch of the tree. The savepoint/re-read never ran. Found by reproducing the race with two concurrent bench processes. Now catches both, plus `frappe.clear_last_message()` so a recovered race stops reporting a failure that did not happen (`0442d66`).

`sync_to_queue` (utils/patient_encounter.py:61-82) looks up / creates one
`Patient Queue` row per `patient` (`get_value(..., {"patient": doc.patient})`),
and `Patient Queue.patient` has a **DB-level unique constraint**
(doctype/patient_queue/patient_queue.json). Two consequences:

1. **Same patient in two sessions the same day** (or a repeat visit while a
   prior visit is still active): the second `sync_to_queue` *reassigns* the
   single queue row to the new encounter/session. The first session's board
   (`get_today_queue` reads `{"clinic_session": session}`, cad_form.py:295-300)
   silently loses the patient mid-visit; the doctor's "Waiting" row becomes
   the other camp's row.
2. **Concurrent first-registrations of the same patient** (two camps, two
   CADS): both `get_value` miss, both `insert`, the second raises
   `DuplicateEntryError`. `create_encounter` catches only
   `frappe.ValidationError` (cad_form.py:284-286), so the losing request
   surfaces a raw 500 and the encounter insert rolls back — the patient is
   not registered.

Also note: `clinic_session` is a `Data` field (no FK) and queue rows are never
cleaned when an encounter/session is deleted, so SM cleanup leaves dangling
rows (see F11).

### F4. MEDIUM — `register_patient` accepts a session in any status

**STATUS 2026-08-26: FIXED and verified live.** `require_running_session` shared with `create_encounter`. All four non-running statuses rejected over real HTTP as a single-role CAD user, plus a covering test at the HTTP boundary.

cad_form.py:146-167: the only gate is `require_session_access` (CAD role +
assigned_driver) — there is **no `status == "In Progress"` check**, unlike
`create_encounter` which enforces it (cad_form.py:242-248). A CAD can
register a patient against a **Cancelled** or a future **Planned** session.
Because the session resolves the permanent Clinic ID prefix
(`resolve_registration_origin`, cad_form.py:138-143 →
`make_clinic_id`, utils/custom_bandhu_id.py:23-32), registering against a
Cancelled camp hardcodes an LSG/unit code for a location the camp never ran,
into a ten-digit ID that is never rewritten once printed on a card.

### F5. MEDIUM — Nurse `start_session` / `end_session` have no status or date machine

**STATUS 2026-08-26: FIXED and verified live.** `load_session_for_status_change`; six negative cases plus a full browser start→end→reopen cycle as a real nurse. See F13 for a residual race inside it.

nurse_form.py:92-110: `require_session_access` checks only that the caller is
the session's `assigned_nurse`; then writes `status`/`start_time`/
`end_time` via `frappe.db.set_value`, **bypassing the `Bandhu Clinic Session`
controller entirely** (bandhu_clinic_session.py:45-63 validates assignment
roles but has no status-transition logic at all). A nurse can therefore:
- mark a session dated *any* day In Progress (it then counts in "Camps
  Running Now", and `find_active_session` — utils/session.py:129-148 — will
  surface it to the staff boards even when it is not today's camp);
- re-open a Completed session (`start_session` again after `end_session`) and
  register/see patients after the camp officially closed, with no audit trail.

### F6. MEDIUM — CAD can search and print ANY patient in the system

**STATUS 2026-08-26: CLOSED by making the access auditable, not narrower** (`ad56469`). Scoping the search would break the feature — a CAD legitimately meets patients registered at other sites. `search_patient` and `get_patient_card_html` now write to frappe's own Access Log via `make_access_log` (deferred insert, so the request is not blocked). Confirmed first that `cad_form.js` fires the search on Enter/button only, not per keystroke, so this is one row per deliberate lookup. **Open policy question: Access Log is not in frappe's `default_log_clearing_doctypes`, so this trail grows unbounded until someone picks a retention.**

`search_patient` (cad_form.py:81-101) returns name / `custom_bandhu_id` /
sex / dob / mobile (the `mobile` and `dob` fields are in the `or_filters`)
for any patient, and `get_patient_card_html` (cad_form.py:107-135) renders
and returns the printable card for any named patient with
`ignore_print_permissions`. Nothing scopes either to the CAD's own session,
unit, or LSG; the `limit=20` is paginated away by querying different terms.
This is deliberate (repeat patients across camps), and the audit brief asked
specifically; but it means the lowest-privilege field role can enumerate and
print PII (incl. ABHA via `search_patient`'s `custom_abha_id` filter and via
`get_patient_details` for any linked encounter) of **every patient in the
DB**. There is no per-CAD scope or account-confinement; a compromised CAD
account is a full read on the patient master. Consider scoping
session-lookup searches, or an access log.

### F7. LOW — Dead third enum `custom_encounter_status` on the encounter

**STATUS 2026-08-26: FIXED upstream in PR #18**, which dropped the dead field with a patch (`patches/remove_dead_encounter_status_field.py`). Note the audit's claim that no code writes it was true of app code only — the field's own default filled it, so every encounter read `Registered` regardless of its real state.

`Patient Encounter.custom_encounter_status` (custom/patient_encounter.json:1278)
is a Select (`Registered / In Consultation / Completed / Referred`) written by
**no code in the app** (grep: only its field definition and field_order). The
state machine that actually drives the board is
`custom_workflow_state` + `Patient Queue.current_stage` (utils/
patient_encounter.py:4-26). If anyone edits it on the Desk form it can silently
contradict the two real enums with nothing to re-sync it — the exact
enum-drift landmine the status log warns about. Either wire it into the
machine or remove the field. Same class: `custom_has_tests`,
`custom_has_prescription`, `custom_has_referral`, `Patient.custom_clinic_id`
(grep: definitions only), and `Patient Queue.handled_by` (never written).

### F8. LOW — `get_districts` whitelisted with no role gate

**STATUS 2026-08-26: FIXED.** Gated with `require_cad_access()` (`7f046a2`). Its only caller is the native-state change handler in `cad_form.js`, which PR #18 had just wired up; covered by a test that calls it as a real CAD user.

utils/state_districts.py:258-274 is `@frappe.whitelist()` with no
`require_*` guard (it reads the `State` master and returns a hardcoded
district list). No PII, no write, static public data — harmless in practice.
Either gate it (CAD) or remove the whitelist if unused (it is not called from
any page JS in this repo).

### F9. LOW — `find_active_session` silently picks one of several same-day sessions

**STATUS: FIXED.** `find_active_session` now resolves ties through an explicit status priority (`utils/session.py`), so the pick is deterministic.

utils/session.py:129-148: when a practitioner has two sessions in one day
(morning + evening camp), the tiebreak is `creation desc`, i.e. **arbitrary**.
The whole doctor/nurse/CAD board is then pinned to that one session
(`get_session_status` → `get_doctor_session` → `find_active_session`,
doctor_form.py:28-39; `get_registered_patients` scoped to it,
doctor_form.py:120-126). Patients in the other camp are invisible to that
staffer's page with no way to switch. Not a security issue — an operational
gap that will surface the day a doctor is scheduled twice.

### F10. LOW — `regenerate_future_sessions` deletes beyond-horizon sessions it never recreates

**STATUS: FIXED.** `remove_unused_future_sessions` resets `last_generated_upto` to `None`, so dates removed from beyond the horizon are regenerated instead of vanishing.

bandhu_session_schedule.py:171-198 deletes **all** future `Planned` sessions
without encounters (any date), then regenerates only up to
`today + horizon_days` (utils/session_schedule.py:176-177, default 56).
Sessions dated beyond the horizon are permanently dropped from staff
schedules until the nightly run's rolling horizon reaches them — the dates
show as empty in "My Schedule" in the meantime. Also: the delete path checks
only `Patient Encounter` linkage, so nothing prevents deleting a session
referenced by a stray queue row (`Data` fields have no FK — see F3/F11).

### F11. LOW — Queue-row lifecycle: Data FKs + no cleanup

**STATUS 2026-08-26: FIXED for the lifecycle half** (`70560e5`). `Patient Queue.clear_old_logs(days=90)` registered through `default_log_clearing_doctypes` — reusing Frappe's Log Settings retention rather than adding a scheduled job. Only `Done` rows are cleared; the queue is a projection that `sync_to_queue` rebuilds from the encounter, and a test asserts the encounter outlives its cleared board row. **Deliberately not done:** the `Data`-typed FK columns were left as-is — converting them to `Link` is a schema change over a unique index, not a cleanup. Ceiling recorded as a `# ponytail:`: rows for a camp a nurse never closed stay `Active` forever.

`Patient Queue.clinic_session` and `patient` are `Data` (not Link), so there
is no referential integrity: deleting an encounter or session leaves a
dangling queue row, and `sync_to_queue` only ever flips `status` to "Done",
never removes the row. `created_on`/`last_updated` are typed `Autocomplete`
(patient_queue.json) — wrong fieldtype for timestamps; harmless for storage,
misleading on the Desk form. Informational.

### F12. INFO — Test coverage gap: role checks yes, HTTP/coercion/concurrency no

**STATUS 2026-08-26: CLOSED.** 20 tests added (`61cd260`, `8c4b75a`), suite 132 → **152**. `test_api_boundary.py` reaches the endpoints the way the browser does — a real `frappe.local.request` through `frappe.handler.execute_cmd`, so `is_whitelisted`, HTTP-method validation and pydantic coercion all run — which is exactly what calling the Python function directly with correct types never exercised. `test_encounter_concurrency.py` covers the stale-save, double-fire and double-submit races. Every test was proven red by mutating the source and restoring it, so none are tautologies.

93 test methods across 9 `test_*.py` files call whitelisted functions
directly under `frappe.set_user`. Ownership/role blocks are genuinely covered
(`test_doctor_form.py:170` another doctor's patient; `test_nurse_form.py:239`
nurse not assigned to session; plain-user blocks). What is never exercised:
the Page `roles` gates (page/*.json) themselves, `@frappe.whitelist` arg
coercion over real HTTP (e.g. `""` for a `float | None`, a JSON string for
`list | str` — the exact failure class that bit `cad_form.js` before), and
double-submit/concurrency (F2, F3). No browser-level tests exist.

---

### F13. MEDIUM — `start_session` is TOCTOU; a concurrent open clobbers `start_time`

**STATUS 2026-08-26: OPEN, found while closing F12.**

`page/nurse_form/nurse_form.py:105-127` — `load_session_for_status_change`
reads `status`/`date` with `frappe.db.get_value`, runs every guard against that
snapshot, then writes with a plain `frappe.db.set_value`: no compare-and-swap,
no row lock. Two requests that both read `Planned` both pass and both write.
Demonstrated with two concurrent opens, the second overwriting the first:

```
first_start  = 2026-08-26 12:24:22.422941
second_start = 2026-08-26 12:24:22.425124
```

Bounded but real: `start_time` feeds the opened/closed/hours columns of Bandhu
Session Report and the "Camps Late To Open" number card, so a double-open
silently shifts a camp's recorded opening. The dangerous direction — a stale
request resurrecting a *closed* camp — does NOT happen and is covered by a
committed test. Fix is a conditional update or `for_update=True` on the status
read.

Lower-severity note from the same pass: an empty string for an optional numeric
surfaces as an unhandled `FrappeTypeError` (500-shaped), not a validation
message. Only reachable if `cad_form.js`'s omit-blank-optionals discipline
lapses; the contract is now pinned by a test either way.

---

## Checks that came back clean

- **SQL injection:** zero `frappe.db.sql` calls in the app; no raw SQL, no
  string-built queries. All reads via `frappe.get_all`/`get_value` with
  filter dicts.
- **AuthN/AuthZ on endpoints:** all 37 `@frappe.whitelist` methods have an
  explicit in-function role gate (`require_cad_access` cad_form.py:10,
  `require_doctor_access` doctor_form.py:10, nurse `require_session_access`
  nurse_form.py:8, `require_schedule_access` my_schedule.py:9,
  `require_scheduling_access` new_schedule.py:27, `require_system_manager`
  staff_onboarding.py:14). No `allow_guest` anywhere. Doctor/nurse/CAD
  `get_session_status` return a benign "no session" payload to wrong roles
  instead of throwing — no data leak.
- **Doctor cannot act on another doctor's patient, nor read their history:**
  `load_owned_encounter` (doctor_form.py:85-94) and
  `verify_patient_linked_to_my_session` (doctor_form.py:138-150) both tie the
  encounter/patient to the caller's own active session.
- **Client-side XSS in the pages:** every dynamic interpolation across all
  six page JS files goes through `frappe.utils.escape_html` (≈70 call sites;
  sampled doctor_form.js:98-597, nurse_form.js:245-565, cad_form.js:240-621,
  my_schedule.js:45-179, new_schedule.js:70-352, staff_onboarding.js:20-149).
- **JS re-bind / listener stacking:** `.off("click")` guards verified before
  every `.on()` rebind — doctor_form.js:217, nurse_form.js:186,
  my_schedule.js:209, new_schedule.js:377; cad_form and staff_onboarding use
  selector-scoped `.off().on()`. The 2026-08-10 double-fire bug is fixed.
- **Background jobs:** the only scheduler task is
  `generate_scheduled_sessions` (hooks.py:151-155). Idempotent — a date
  already carrying a session is never regenerated whatever its status
  (utils/session_schedule.py:183-191); per-schedule savepoint rollback +
  `log_error`, one bad schedule can't kill the run (215-219); horizon bounded
  (default 56d, utils/session_schedule.py:23,150-152). No `frappe.enqueue`,
  no `enqueue_after_commit` — generation is synchronous and atomic per save.
- **Schedule date maths:** fortnightly parity anchored to `valid_from`,
  nonexistent 5th weekdays skipped not shifted, holidays excluded,
  `day_of_month` guarded to the last day of each month
  (utils/session_schedule.py:64-147).
- **Time formatting:** every Time→browser crossing is zero-padded —
  `clock_value` (new_schedule.py:110-116) for `<input type="time">`,
  `formatClockTime` for display (doctor_form.js:153-157, nurse_form.js:273-277,
  my_schedule.js:34-41).
- **No naive datetime use:** no `datetime.now()`/`today()`; everything is
  `frappe.utils.today()/now_datetime()/now()`. Phone numbers validated
  (`validate_phone_number` + 10-digit regex), BMI computed in `validate`
  (utils/patient.py:5-11), ID serial via atomic `getseries` with a hard
  ceiling throw (utils/custom_bandhu_id.py:35-46).
- **Migration patches:** `regenerate_patient_qr_codes` is a bounded,
  transaction-safe regen; the LSG/Unit numeric-code patch is seed-only (no-op
  on a fresh DB unless exact names exist). `patches.txt` is well-formed.
- **Schema ↔ code:** all fields read/written by the page methods and utils
  exist in the doctype/custom JSONs (spot-verified end to end: Test
  Instructions, Prescription, Bandhu Diagnosis, Patient Queue, encounter
  custom fields). Child tables (`test_instructions`, `prescription`,
  `bandhu_diagnosis`, `services_provided`) correctly carry no permission rows
  (inherited from parent).
- **Workflow machine integrity on Desk edits:** `validate_workflow_state` is
  registered as a `doc_events` validate hook (hooks.py:262), so it runs on
  *every* save including Desk-form edits, not just the page methods — the
  forward-only machine holds even if a privileged user bypasses the pages.

---

## Could not check (read-only audit)

- **Live DB state:** whether any `Patient Queue` / encounter enums are
  actually drifted right now; whether the 5 "left open" sessions are still
  `In Progress`; whether Drug Items are `is_stock_item=0` (no Bin/ledger → the
  known low-stock blocker); whether `Patches` are all marked applied.
- **HTTP layer behaviour:** the Page `roles` gates, whitelist arg-coercion
  failures, and double-submit behaviour are inferred from code only — never
  executed against the site (F2, F3, F12 rely on this).
- **Dashboard rendering:** Number Cards' `dynamic_filters_json` is `eval`'d
  client-side (`frappe.utils.dashboard_utils`); the cards' static/dynamic
  filters were verified structurally (e.g. "Patients Seen Today" filters
  `encounter_date = get_today()`, "Camps Left Open" filters
  `status=In Progress` and `date < get_today()`) but the rendered page was not
  viewed.
- **Frappe-internal locking:** whether `frappe.client.save`/`Document.save`
  in this Frappe version adds any hidden timestamp check to the direct
  `doc.save()` calls in the page methods (none found in the app code itself).
- **Print rendering:** the stored-XSS payload (F1) was not actually fired —
  mechanism verified from `frappe.utils.jinja.py:56` (autoescape off) and
  `cad_form.js:214-220` (same-origin `document.write`), not by executing it.

---

## Where this stands (2026-08-26)

11 of the 12 original findings are closed: F1, F3, F4, F5, F6, F7, F8, F9, F10,
F11 fixed, F2 dismissed as not-a-defect with a regression test behind the
dismissal. F12 is closed by the 20 tests it asked for. **F13 (above) is open.**

Two of these were recorded as fixed on 2026-08-15 and were not: F1 was
re-opened by PR #18 rewriting the card template, and F3's `except` clause named
an exception the code never raises. Both were caught by executing the failure,
neither by re-reading the diff. Treat a status line here as a claim to re-test,
not as evidence.

---

## Priority fix order

1. F1 (one-line `|e` escape in the print template — removes a real XSS).
2. F2 (backend transition guard — already bit once in prod).
3. F3 (queue keying / duplicate-insert handling).
4. F4 + F5 (status/date enforcement on register + nurse start/end).
5. F6 (scope or log CAD-wide patient reads).
6. F7–F11 as cleanup, next time the schemas are touched.
