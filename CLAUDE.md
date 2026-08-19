# bandhu_app — Project Instructions

Owner: CMID (Bandhu Mobile Clinics). We took over ownership of this project
from the prior dev.

## Write like a senior engineer, not like AI

Every line of code and every comment in this repo should read like it was
written by a 20-year senior engineer who knows this codebase cold — not
like a low-effort model output. Concretely:

- **Async/await, not callbacks**, in all Frappe JS: `const r = await
  frappe.call({...})`, not `frappe.call({..., callback: function(r) {...},
  error: function(){...}})`. Nested callbacks are exactly the pattern that
  reads as dated/generated — modern `frappe.call` supports awaiting it
  directly. Applies to every `.js` file in this app, Desk or website page.
- **No meaningless leading underscores.** `_foo` is fine ONLY when it
  signals something real (a private helper never meant to be imported
  elsewhere) — not sprinkled by default. When renaming, check nothing
  else imports the name first.
- **Full, meaningful names.** `packing_slip_info`, not `ps_info`. Avoid
  single-letter params (`r`, `p`, `f`) in new code even where the old
  codebase used them — don't propagate a bad existing pattern into new
  code just because it's already there.
- **snake_case for functions/variables, always** (PascalCase is for
  classes only — Frappe's own DocType controller classes are the one
  legitimate exception, that's the framework's convention, not ours).
- **Comments explain *why*, never *what*.** No section-divider banners,
  no restating the line below it, no comment that would still be true if
  the code changed. Delete a comment if it doesn't survive "would a
  senior engineer actually write this down."
- **Never override Frappe's `Document` base class internals** (`insert`,
  `save`, `db_insert`, etc.) — use the hooks the framework already gives
  you (`validate`, `before_save`, `on_update`, doc_events in hooks.py).
  Defining `validate()` on your own DocType's controller is the intended
  pattern, not an override in the risky sense — the ban is on reaching
  into Frappe's own base classes, not using your own controller's hooks.

Source: https://bwh.tech/ai-etiquettes/how-to-use-llm-in-bwh — the client's
own AI-usage standard for this codebase. Non-negotiable, checked on every
PR. Apply it by default, don't wait to be asked per-file.

## Core Rules

Act as a staff engineer, 20 years, many stacks and companies. Judgment about
consequences, not recall of syntax.

### Caveman Mode
- No filler, greetings, sign-offs, or restating the question.
- Code speaks for itself — no explanation unless asked.
- Max 1 sentence before output. Stop after it. No "let me know if you'd like...".
- No flattery. If wrong, first sentence says so.

### ⚠ Lines — the one exception
Brevity is suppressed output, not suppressed judgment. Warn BEFORE running it,
not after. One line each, max 2 per response, no elaboration unless asked:

    ⚠ ALTER on users locks the table; ~40s downtime at current row count.
    ⚠ Retry has no cap; upstream 500s become a retry storm.

Specific mechanism → specific consequence. "May have performance implications"
is worthless. Trigger on: data loss, one-way doors, auth boundaries, silent
failure, money, unbounded anything, live migrations, secrets. Not on style.
>2 warnings = drop Caveman Mode, say so.

### Never fake
Never invent APIs, flags, config keys, versions, or library behavior. Unsure
→ one line: what's unknown, what resolves it. State assumptions inline
("assuming Frappe v16 —"), don't bury.

### Context
- Don't read files >200 lines whole. grep/glob to the section, read that range.
- Never edit code not read. Do not infer surrounding code. 40 lines read beats
  a guess.
- Whole large file genuinely needed → name it, say why, ask.
- Long outputs to disk, not inline.
- Codebase search → `Explore` subagent (haiku, read-only). Keeps window clean.

### Session
- Checkpoint to `.claude/checkpoint.md` on task completion or before
  `/compact` — not on a tool-call count. Changed / next / blockers. Overwrite.
  Gitignore it.
- Dead context piling up → suggest `/compact`. Unrelated task → suggest new
  session.

### Never
- Abstraction before 3 real call sites. Rewriting working code structured
  differently than preferred.
- Swallowed exceptions. Bare catch. Logging-and-continuing on unrecoverable
  state.
- New dependency where 20 lines of stdlib do.
- User input into SQL / shell / HTML / file paths. Secrets in code, config,
  or logs.
- `sleep()` as sync. Retries without backoff, jitter, cap.
- Unbounded queues, caches, result sets. Missing pagination.
- Naive timestamps. Local time in storage. Floats for money.
- Migrations that lock big tables or break rolling deploys.
- Tests asserting implementation details, or asserting nothing.
- `// TODO` inside code presented as finished. Mark deliberate omissions.
- Symptom fix when root cause is one layer down — ⚠ it, then fix what was
  asked.
- Unflagged scope creep: days of work disguised as one question → say so
  before starting.

## What this is
Mobile clinic (field health camp) MIS on Frappe + ERPNext + Healthcare.
Site: `bandhuapp.local`. App module root: `bandhu_app.bandhu_app`.
Roles: CAD (front desk), Doctor, Nurse, Programme Manager/System Manager.
Full scope doc: see CMID scope-of-work (developer's copy in chat history).

## LEARNINGS.md
`LEARNINGS.md` in this directory holds Frappe CRM reference-architecture
notes (frontend/backend patterns worth adopting). Consult it only when a
task needs prior art from Frappe CRM's feature set — not required reading
otherwise.

## Known landmine (don't rediscover this the hard way)
State lives in parallel enums (`Patient Queue.current_stage`,
`Patient Encounter.custom_workflow_state`, `custom_encounter_status`) that
can drift. `LEARNINGS.md` §4 has the full picture and current fix status.

Frappe's Jinja environment has autoescape **off** (`frappe/utils/jinja.py:56`
builds `FrappeSandboxedEnvironment` with no `autoescape=True`), so every `{{ }}`
in a print format or template that carries user-entered data needs `| e`. The
page JS is disciplined about `frappe.utils.escape_html`; that discipline does
not carry across into Jinja, and the miss is silent until someone prints.

## Working agreement
- Take ownership: make sensible low-risk assumptions, implement the full
  in-scope change, verify it (run the relevant tests/migration, not vibes).
- Preserve existing uncommitted work already in the tree — this repo has
  live uncommitted changes from the handoff; don't clobber without reading
  first.
- Follow Frappe conventions: use framework APIs (permissions, validation,
  naming, links, transactions, caching) instead of bypassing them.
- Schema/data changes need patches/fixtures/migrations, not manual DB edits.
- Ask before: deleting data, overwriting unrelated in-flight work, touching
  production/external systems, or a product decision that isn't inferable.

## Keep this file current
Update the Status log below on milestone completion, architecture change, or
fixing a known gap — so the next session starts from real state, not stale.
Overwrite in place, don't append noise.

## Status log
- 2026-08-10: Took ownership. Existing site `bandhuapp.local` had
  `bandhu_app` installed with uncommitted WIP — reset to clean
  `upstream/main` (6c50c76) at the user's request; the WIP (state-sync fix,
  permission checks, N+1 batching, CAD form) was discarded, `LEARNINGS.md`
  kept but marked roadmap items 1/2/3/5/6/8 back to NOT DONE. Replaced
  `AGENTS.md` with this file.
- 2026-08-10: Rebuilt the core clinic loop from scratch (uncommitted, not
  yet in git):
  - `utils/patient_encounter.py`: `ALLOWED_TRANSITIONS` forward-only state
    machine + `sync_to_queue` (keys on `patient`, not `encounter` —
    `Patient Queue.patient` has a DB-level unique constraint, one live
    board row per patient, overwritten each visit).
  - `page/cad_form/`: new — patient search/register, create encounter,
    today's queue board.
  - `doctor_form.py/js`: `advance_patient` (Order Test / Prescribe
    Medicine / Mark Complete), session-ownership gated.
  - `nurse_form.py/js`: `complete_test` / `complete_medicine`,
    session-ownership gated.
  - 14 integration tests across the three modules, all passing.
  - Fixed 3 bugs found only by actually clicking through the UI (not by
    the unit tests, which called Python functions directly with correct
    types/DB state and so didn't hit these):
    1. `cad_form.js` sent blank optional numeric fields as `""` over HTTP;
       this bench enforces typed API args (`float | None` rejects `""`).
       Fixed: omit empty-optional keys from `args` entirely.
    2. `custom_workflow_state` on Patient Encounter was defined as
       `fieldtype: Link` → `options: "Workflow State"` in
       `custom/patient_encounter.json`, but every piece of code (mine and
       the agents') treats it as a fixed 5-value enum and never creates
       `Workflow State` master records. This was dormant until
       `bench migrate` synced the on-disk (wrong) fixture into the DB.
       Fixed at the schema level: changed to `fieldtype: Select` with the
       5 literal options — not a Link to an unrelated generic master.
    3. `patient_name`/`patient_sex`/`patient_age` on Patient Encounter are
       plain fields the standard Healthcare app only populates via the
       Desk form's client-side fetch-on-change JS, or via
       appointment-mapping. A bare server-side `.insert()` (what
       `create_encounter` does) triggers neither, so these showed blank
       on the Doctor/Nurse boards. Fixed: `create_encounter` now sets them
       explicitly from the Patient doc (`patient.get_age()` is the
       framework's own canonical age-formatting method).
  - Full loop verified twice: once via `bench execute` (repeat-visit
    scenario — confirms the unique-constraint fix), once via a real
    browser click-through (CAD → Doctor → Nurse → Doctor → Nurse →
    Completed), both fixes applied live and reconfirmed with the browser
    run, not assumed from the unit tests alone.
  - Still open: `get_patient_histories` batching (doctor_form N+1) was
    flagged as a follow-up by the doctor agent, not done. Repeat-patient
    encounter creation in `cad_form.create_encounter` dedupes on
    `(patient, session)` but hasn't been driven through the browser for a
    genuine same-day repeat visit — only the single-visit path and the
    backend repeat-visit unit check are confirmed.
- 2026-08-10: Real multi-user role-isolation test (3 dedicated users —
  `cad.tester@bandhu.local` / `doctor.tester@bandhu.local` /
  `nurse.tester@bandhu.local`, each with exactly one role, `Test@1234`,
  linked to the day's session practitioners), driven sequentially through
  the actual login flow (not Administrator+temp-link impersonation —
  System Manager bypasses all permission checks so that never proved
  isolation). Confirmed: each role's Page-level `roles` gate blocks the
  other two pages outright ("Not permitted", before any app code runs);
  each user could only act within their own role. 4 patients run through
  varied paths (direct-complete, order-test, prescribe-medicine) to
  exercise all transition branches.
  - Found and fixed a real concurrency bug this way: `doctor_form.js` and
    `nurse_form.js` re-bind `page.main.on("click", ...)` on every
    `render()` (which fires after every action, not just on load) without
    ever calling `.off()` first. `page.main` is a persistent DOM node —
    `.html()` replaces content but not delegated listeners already bound
    to the container — so each render stacks another handler, and after
    enough renders one click fires the callback N times. Hit this live: a
    double-fired `advance_patient` on the same encounter produced a real
    MariaDB error 1020 / Frappe `QueryDeadlockError`
    ("Record has changed since last read") from two racing `doc.save()`
    calls. Fixed both files: `page.main.off("click")` before every
    `.on()` rebind. `cad_form.js` already did this correctly per-selector
    (`.off(sel).on(sel, ...)`) — no bug there.
  - Not yet covered: no automated regression test for the double-bind bug
    (it's a frontend event-wiring issue, not easily unit-tested through
    Frappe's backend test framework — would need a Playwright-style
    browser test). If this pattern (re-render + re-bind) gets copied into
    a new screen, re-check for the same `.off()` omission.
- 2026-08-11: **Correction added 2026-08-12** — the www-page conversion this
  entry describes does not exist in the current code. There is no `www/`
  folder in this app; `page/cad_form`, `page/doctor_form`, `page/nurse_form`
  (Desk Pages, routed at `app/cad-form`/`app/doctor-form`/`app/nurse-form`)
  are the real, current working pages. Either this was reverted after being
  written up, or written up before it was actually done — unclear which,
  and not worth reconstructing at this point. A 2026-08-12 session trusted
  this entry at face value, pointed `role_home_page` and a new redirect
  script at `/cad`/`/doctor`/`/nurse`, and those 404'd live. Lesson: verify
  status-log claims against the filesystem before building on them — see
  the 2026-08-12 entry below for the corrected state.
- 2026-08-11: Converted CAD/Doctor/Nurse from Desk Pages to plain website
  pages (`www/cad.py`+`.html`, `www/doctor.py`+`.html`, `www/nurse.py`+`.html`,
  matching JS in `public/js/{cad,doctor,nurse}_web.js`) at the user's
  request — no Desk chrome (sidebar/search bar/notifications) for
  non-technical field staff, just the screen itself. `role_home_page` in
  `hooks.py` now points at `cad`/`doctor`/`nurse` (bare paths, no `app/`
  prefix — these are website routes, not Desk routes). Verified live via
  real login as each of the 3 test users: lands directly on the right
  page, zero chrome, full CAD→Doctor→Nurse flow works. Backend whitelisted
  methods are completely unchanged — same `page/*_form/*.py` files, only
  the frontend shell changed. Desk-only JS APIs not available outside the
  Desk bundle were reimplemented page-scoped: `frappe.dom.freeze/unfreeze`
  (same reference-counted semantics as the real one, to not reintroduce
  the earlier stuck-frozen-screen bug), `frappe.call` itself (needs
  `request.js` loaded explicitly, included via each page's `.html`).
  `frappe.set_route` (Desk's SPA router) replaced with a plain link to
  `/app/patient-encounter/<name>` as the "view raw record" escape hatch.
  - **Incident, now resolved**: deleted the *old* Desk-shell `.js`/`.json`
    files for all 3 pages via `rm`, intending to keep the `.py` files
    (still used by the new frontend, endpoints are just dotted Python
    paths, don't care what frontend calls them). The next `bench migrate`
    detected the orphaned `Page` doctype records and deleted the **entire
    folder from disk**, not just the DB record — including
    `cad_form.py`/`doctor_form.py`/`nurse_form.py`, none of which were
    committed to git (nothing in this app is committed yet). Recovered by
    reconstructing all three files from: git's `upstream/main` baseline
    (doctor/nurse only — cad_form.py never existed pre-reset, no baseline
    at all), the documented behavior from each file's own session history
    in this log, and the exact method/arg names encoded in the surviving
    `*_web.js` files and `test_*.py` files (which were NOT inside the
    deleted folders and survived intact). All 24 tests plus a full live
    browser walkthrough of all 3 pages confirmed the reconstruction
    correct. **Lesson**: never delete files inside a Frappe `page/<name>/`
    folder piecemeal — `bench migrate`'s orphan-page cleanup treats the
    whole folder as disposable once its `.json` is gone, even if other
    files in it (like a `.py` with unrelated whitelisted methods) are
    still load-bearing. If a page's `.py` needs to survive the page's
    death, move it OUT of the `page/<name>/` folder first, then delete the
    folder — don't delete in place and migrate.
  - Old Desk Pages (`/app/cad-form` etc.) are fully gone — Page DB records
    deleted, folders deleted, `role_home_page` repointed. Nothing links to
    them anymore; the CAD/Doctor/Nurse Desk *workspaces* (icon-grid tiles)
    are separate, unrelated records (link to Patient/Vehicle/Referral
    doctype lists, not to these pages) and were not touched.
  - Still nothing in this app is committed to git. That would have made
    this incident a non-event (`git checkout` instead of reconstruction) —
    worth doing soon.
- 2026-08-11: Real user hit "Could not find Native State: karnatak, Sector
  of Employment: labur / Failed to register patient." during live CAD
  testing. Root cause: `custom_native_state` (→ `State`) and
  `custom_sector_of_employment` (→ `Sectors`) are genuine Link fields on
  Patient, but the CAD form rendered them as free-text `<input>` — any
  typo or value outside the curated master list crashed registration with
  a raw Link-validation error. Compounding: the `State` master only had
  "Kerala" seeded, even though `utils/state_districts.py` already ships
  real district data for 6 migrant-source states (Bihar, UP, Tamil Nadu,
  Assam, Odisha, West Bengal) that were never turned into `State` records
  — dormant data, never wired up.
  - Fixed both halves: seeded the 6 missing states (`is_major_state=1`)
    and added a "Other" `Sectors` entry as a catch-all; added
    `get_form_options()` to `cad_form.py` (returns real state/sector
    lists) and changed `cad_web.js` to render actual `<select>` dropdowns
    for these two fields instead of text inputs, fetched once in
    `load_dashboard` before the register form can ever open.
  - `custom_native_district` is `Autocomplete`, not `Link` — free text
    never crashes it, so left as-is; `get_districts()` in
    `state_districts.py` exists for state-scoped district autocomplete
    but isn't wired into the CAD form yet (nice-to-have, not a bug).
  - Verified: 9/9 cad_form tests (2 new: `get_form_options` returns real
    masters, `register_patient` rejects a state not in the master), full
    live re-submission of the exact reported scenario (now via dropdown),
    confirmed saved correctly server-side.
  - **Pattern to watch for elsewhere**: any other free-text field on the
    CAD/Doctor/Nurse forms that maps to a real Link field server-side is
    the same landmine waiting to happen. Worth an audit pass over
    `custom/patient.json` and `custom/patient_encounter.json`'s Link
    fields against what each form actually renders, rather than waiting
    for the next one to surface live.
- 2026-08-11: User pointed at the client's own AI-usage standard
  (https://bwh.tech/ai-etiquettes/how-to-use-llm-in-bwh, now folded into
  this file's "Write like a senior engineer" section above) and asked
  whether this session had violated it. It had, in one clear way: every
  `frappe.call` in `cad_web.js`/`doctor_web.js`/`nurse_web.js` (and the
  Desk-page `.js` files before they were retired) used the old
  `callback`/`error` option pair instead of `await frappe.call(...)`.
  Converted all three files to async/await. Also removed the leading
  underscore from module-private helper names across `cad_form.py`,
  `doctor_form.py`, `nurse_form.py` (`_require_cad_access` ->
  `require_cad_access` etc.) — confirmed nothing outside each file
  imported the underscored names before renaming.
  - **Real bug caught while converting, not by inspection**: `frappe.call`
    returns the underlying `$.ajax` promise, which rejects with the raw
    jqXHR object, not a clean `{message}` shape — `e.message` on a caught
    rejection is `undefined`. Verified live in the browser. Separately
    discovered that `frappe.request.cleanup()` (wired into every
    `frappe.call` via `.always()`) already calls `frappe.msgprint()` with
    the server's real error text automatically, for every failed call —
    confirmed by awaiting a call designed to fail and watching the exact
    right dialog appear with zero manual message handling. This also
    retroactively explains the *original* CAD registration bug report:
    the old code's generic `error: function(){ frappe.msgprint("Failed to
    register patient.") }` was firing ON TOP OF the framework's own
    automatic message, which is why that first screenshot showed two
    messages stacked in one dialog. Removed all the now-redundant manual
    `frappe.msgprint` calls in catch blocks (kept the framework's own
    display, catch blocks now only handle `frappe.dom.unfreeze()` and
    stopping further flow) — fewer lines, no double-dialogs, and the
    accurate server message reaches the user instead of a generic one.
  - Also used `Promise.all` to replace the manual `done++`/`check_done()`
    parallel-call-counting pattern in `doctor_web.js` (patient histories)
    and `nurse_web.js` (tests/medicines/completed, in loadQueues) — a
    genuine readability improvement that fell out of the modernization,
    not extra scope.
  - Verified: all 26 backend tests still pass (naming rename didn't touch
    any cross-file import), `node --check` on all 3 rewritten JS files,
    full live walkthrough of CAD register -> Doctor complete -> Nurse
    start-session/mark-test-done, all working.
- 2026-08-12: Desk-icon UX pass. User wanted clicking CAD/Doctor/Nurse's icon
  on `/desk` (the app grid) to land straight on the real working page, no
  extra navigation, and wanted login to land on the plain Desk icon grid
  (not auto-redirect into the working page — that was tried first and
  explicitly reverted at the user's request).
  - `public/js/workspace_redirect.js` (new, wired via `app_include_js`):
    listens on `frappe.router.on("change", ...)`, and when the resolved
    route is the CAD/Doctor/Nurse Workspace, calls
    `frappe.set_route("cad-form"/"doctor-form"/"nurse-form")` — the real
    Desk Page route. Verified live via Playwright with real
    `cad.tester`/`doctor.tester`/`nurse.tester` logins: icon click and
    direct `/app/<workspace>` URL entry both redirect correctly; unrelated
    workspaces (Admin) are untouched; no redirect loop.
  - `role_home_page` in `hooks.py`: first pointed at `app/doctor-form` etc.
    (correcting the stale www-page entries above), then removed entirely
    per the user's explicit follow-up ask — Doctor/Nurse/CAD now log in to
    the plain Desk icon grid like any other role, same as before this
    session, with the icon-click redirect above doing the rest.
  - **Cache gotcha hit live**: `app_include_js` raw file paths aren't
    versioned by Frappe (`include_script()` only adds `?ver=` for bundled
    assets) — a user's browser kept running the pre-fix JS after the
    server-side fix had already shipped, because nothing forced a refetch.
    Fixed by bumping `?v=2` on the include path in `hooks.py`; needs a
    manual bump on every future edit to this file until it's moved into
    the esbuild bundle pipeline.
  - Workspace visibility scoped: `CAD`/`Doctor`/`Nurse` workspaces
    restricted (via each workspace's `roles` table) to their own role +
    System Manager; `Admin`/`Bandhu`/`Dashboard`/`Inventory`/`Pharmacist`/
    `Referrals` restricted to System Manager only (no `Programme Manager`
    or `Pharmacist` role actually exists in this system — checked the live
    Role table before assuming one, per the user's "no Programme Manager
    role" gap noted informally). Then further scoped per a live follow-up:
    Doctor/Nurse/CAD were still seeing `Framework`/`Quality`/`Marley
    Health` — Desktop Icon records owned by frappe/erpnext/healthcare, not
    this app. Restricted those to System Manager too, via a new
    `bandhu_app/bandhu_app/utils/desk_visibility.py` +
    `after_migrate` hook (not a direct edit to those other apps' files,
    which the top-level CLAUDE.md bans) — this re-applies on every migrate
    since each app's own migrate cycle re-syncs its own Desktop Icon
    fixture and would otherwise silently wipe the restriction.
    - Known follow-up: after this, System Manager/Administrator stopped
      seeing `Framework`/`Quality` on `/desk` (unintended — should still
      see them), while `Marley Health` correctly still shows. Root cause
      not nailed down — looks related to `parent_icon`/nesting behavior
      specific to those two, not the roles restriction itself, which
      tested correctly for Doctor/Nurse/CAD in every case. Low priority
      (Administrator can still reach `/app/build` and `/app/quality`
      directly) but open.
  - **Real incident, caught fast**: mid-way through the above, a plain
    `bench --site bandhuapp.local migrate` (no special flags) triggered
    Frappe's orphan-cleanup step (`remove_orphan_entities` in
    `frappe/model/sync.py`) and it deleted all 9 `bandhu_app` Workspace
    JSON files from disk — not just DB rows, the files — despite them
    being present and valid on disk at the time; two earlier plain
    migrates in the same session had NOT triggered this, so it's
    intermittent and the exact trigger isn't understood. Caught within
    seconds by checking `find` output right after; recovered instantly
    with `git checkout` since these files were already committed
    (`d5c8c07`) — a very different outcome from the 2026-08-11 incident
    above, where nothing was committed and reconstruction from scattered
    sources was the only option. **This app being committed to git is
    what turned a second identical class of incident into a non-event.**
    Redid the workspace `roles` edits and synced them with
    `bench --site bandhuapp.local execute frappe.reload_doc --args
    "['bandhu_app', 'workspace', '<name>']" --kwargs "{'force': True}"`
    instead of a full migrate — this targeted path did not trigger the
    orphan-cleanup step in either of two more attempts. **Going forward:
    no bare `bench migrate` on this site for Workspace/Page/Report
    changes — use `frappe.reload_doc(..., force=True)` per doc. Only run
    a full migrate for an actual schema change, and only with the working
    tree committed first.**
  - Verified end-to-end with Playwright throughout (real test-user logins,
    not Administrator bypass): DOM content checks on landed pages (not
    just URL matching — caught the first, wrong `/doctor` 404 fix this
    way), icon-grid contents per role, no regression for System Manager.
  - Still nothing beyond `d5c8c07` committed — the icon-redirect JS,
    hooks.py changes, workspace roles, and `desk_visibility.py` are all
    uncommitted as of this entry.
- 2026-08-13: CMID call produced 5 new requirements (auto-scheduled recurring
  sessions, admin/monitoring dashboard, printable QR patient card, donor-fund
  pharmacy tracking, low-stock alert). Started with low-stock, hit a hard
  blocker, switched to the QR card and finished it.
  - **Low stock alert is blocked on a missing foundation, not on the alert.**
    All 5 Drug items (`IFA100`, `CETI10`, `AMOX250`, `ORS001`, `PARA500`)
    have `is_stock_item = 0`, so ERPNext keeps no Bin and no ledger for any
    medicine — there is no quantity to alert against. Compounding it,
    `Bandhu Medication Dispense` only flips a `dispensed` checkbox and never
    creates a Stock Entry, so stock would never fall even if it were
    tracked. No warehouse is linked to Clinic/Site/Unit/Vehicle either.
    Parked pending client answers on warehouse layout, zero-stock dispense
    behaviour, and alert recipients. The same foundation is what the
    donor-fund tracking requirement needs, so it is not wasted work.
  - **New 10-digit Clinic ID**, per CMID's spec:
    `LSG(2) + Unit(1) + Year(2) + Serial(5)`, e.g. `0112600002`. Existing
    `lsg_code` / `unit_code` were text (`LSG-EKM-KLM`, `Unit-1-Outreach-Team`)
    and unusable as digits, so new `lsg_numeric_code` / `unit_numeric_code`
    fields were added alongside rather than overwriting them. Both become
    immutable once any ID has been issued against them — every printed card
    embeds the code, so changing it would make circulating cards decode to
    the wrong location.
  - Serial resets per calendar year and runs global across LSG and unit. It
    is deliberately NOT scoped per LSG/unit: those attributes get corrected
    and reorganised, and scoping a permanent identifier to a mutable
    attribute forces the ID to either change or start lying. Drawn from
    Frappe's atomic Series counter (`getseries`), never `max(id)+1`, which
    races under concurrent registration. Throws rather than silently
    widening past 99,999 in a year.
  - `Bandhu Clinic Session` had no `unit` field at all, so nothing in the
    registration path could resolve which unit a patient belonged to. Added
    one, rather than deriving it from `Unit.cad` which breaks as soon as one
    CAD works across two units. `register_patient` now takes the session and
    is gated with `require_session_access` — the session decides which codes
    land in a permanent ID, so the role check alone was not enough.
  - The 42 pre-existing `BMC-xxxxx` patients keep their IDs. Issued IDs are
    never rewritten; search and the scan matcher accept both formats.
  - **QR payload was wrong**: it encoded
    `/api/method/bandhu_app.api.get_patient_by_uid?uid=...`, so scanning a
    card showed a raw JSON blob or a login page. Now encodes the bare Clinic
    ID, which is what a USB barcode scanner needs (it is a keyboard — it
    types the ID and presses Enter). A patch regenerates every existing
    patient's QR image.
  - New `Bandhu Patient Card` print format (86x54mm, CR80). `wkhtmltopdf` is
    not installed on this bench, so it is set to `pdf_generator: chrome`;
    Frappe downloads its own headless shell on first use. QR verified to
    decode off the rendered card at 150/300/600 dpi.
  - Print had to go through a whitelisted endpoint: the CAD role holds **no**
    Patient DocType permission at all (the whole CAD page bypasses Patient
    perms behind role-gated methods), so `/printview` returned "Not
    Permitted". `get_patient_card_html` renders it behind
    `require_cad_access()` using `frappe.flags.ignore_print_permissions`,
    Frappe's own flag for rendering on behalf of an already-authorised
    caller. Worth revisiting whether CAD should simply hold Patient
    read+print instead of every endpoint re-implementing the gate by hand.
  - No print dialog after registration, at the user's request — a prompt is
    wrong when the card is not needed at that moment. Instead every Today's
    Queue row carries the patient's grouped Clinic ID and its own Print Card
    button, so the card can be printed at any point in the visit; the
    registration itself only raises a non-blocking toast. Healthcare's own
    "Customer X created and linked to Patient" toast still fires and is
    noise for field staff — suppressible with `frappe.flags.mute_messages`
    around the insert, but that would also hide genuine msgprint warnings,
    so it was left alone.
  - Verified live with Playwright as `rahul.cad@bandhuclinic.test`, not just
    unit tests: registration through the real UI issued `0112600002` with
    the correct blocks, a typed ID + Enter jumped straight to the confirm
    dialog instead of a result list, and Print Card opened the card without
    also queueing the patient. 56 tests pass.
  - Synced with `frappe.reload_doc(..., force=True)` + `sync_customizations`,
    never a bare `bench migrate`. All 9 workspace JSON files intact after.
  - **"Multiple Loyalty Programs found" dialog on patient registration —
    fixed.** Two `Loyalty Program` records (`Test Multiple Loyalty`,
    `Test Single Loyalty`) belonging to `_Test Company`, both with
    `auto_opt_in = 1` and no customer-group or territory filter, so they
    matched every customer. `Customer.validate` calls `set_loyalty_program`,
    which msgprints when more than one program applies — and ERPNext's
    `get_loyalty_programs` does not filter by company, so a test company's
    programs reached CMID's patients. This is residue from running
    ERPNext's test suite against this site, same source as the 20
    `_Test Company` records and 117 warehouses; it will not exist on a fresh
    site. Set `auto_opt_in = 0` on both rather than deleting them, so it is
    reversible. Deliberately NOT written as a patch — it is dev-site test
    residue, not an app-level migration. Verified with a live registration:
    the only dialog left is the intended "Print this patient's card now?".
    If it ever returns, a test run recreated the records.
  - Pre-existing and not from this work: a `/undefined` 404 fires on the Desk
    landing page.
  - Still uncommitted, along with everything from the 2026-08-12 entry.
- 2026-08-14: Auto-scheduled recurring clinic sessions (CMID requirement 1). The
  client's "Weekly site list 8 June 2026.xlsx" is a site master (29 sites ×
  Location/LSG/PHC-CHC), not a rota — no day, no time, no unit — so the schedule
  is configured by the client in the app rather than transcribed from a file.
  - New `Bandhu Session Schedule` (+ `Bandhu Session Weekday` child, `Bandhu
    Settings` single) and `utils/session_schedule.py`. Weekly / Fortnightly /
    Monthly, with monthly as either nth-weekday or day-of-month.
    `scheduler_events` in `hooks.py` is live for the first time — this is the
    app's first scheduled job.
  - `Bandhu Clinic Session` gained `session_schedule`, `planned_start_time` /
    `planned_end_time`, and a `Cancelled` status. The existing `start_time` /
    `end_time` are real timestamps set by the nurse, so they could not double as
    planned times.
  - **Idempotency key is `(session_schedule, date)`, and a date that already
    carries a session is never regenerated whatever its status.** That is what
    makes a session cancelled for a holiday stay cancelled instead of reappearing
    on tonight's run — the Cancelled row is the tombstone, so no separate
    exception table exists.
  - **Landmine found live: a Single stores nothing until it is first saved, and
    `frappe.db.get_single_value` casts a missing Check to `0`.** A positive
    `auto_generate_sessions` flag was therefore indistinguishable from "switched
    off", and the first live run silently generated nothing despite
    `"default": "1"` in the JSON. Fixed by inverting it to
    `disable_auto_session_generation`, which needs no bootstrap row. Any future
    Check on a Settings single should be phrased as an opt-out for the same
    reason.
  - Doctor and Nurse pages now show "Your Upcoming Sessions" in the
    no-session-today empty state, via `find_upcoming_sessions` in
    `utils/session.py`.
  - Verified: 73 tests (17 new), plus live Playwright — schedule form
    preview/save/generate as Administrator, and the upcoming card as
    `priya.doctor` / `anu.nurse`. The live run caught what the tests could not:
    Frappe serialises a Time as `9:30:00`, not `09:30:00`, so truncating to 5
    characters printed `9:30:`.
  - Synced with `frappe.reload_doc(force=True)` and
    `scheduled_job_type.sync_jobs` — never a bare `bench migrate`. All 9
    workspace JSON files intact afterwards.
  - Next: seed the 29 real sites / 25 locations from that spreadsheet (note
    `Perumbavoor` spans two LSGs, so Location alone is not a key), and get the
    client's LSG numbering for the 18 real LSGs — permanent, printed on every
    patient card, only 3 codes exist today.
- 2026-08-14: "My Schedule" — field staff can now see where and when they are
  expected without opening a Desk doctype list. New shared Desk page
  `page/my_schedule/`, reached from a primary-action button on the Doctor,
  Nurse and CAD pages.
  - Rows read like a calendar entry (`Mon 17 Aug · in 3 days`, site, LSG +
    district, time window, unit), grouped by month; tapping one expands the
    area, LSG, district, nearest PHC-CHC, clinic, unit, vehicle and the team
    that day with tap-to-call numbers.
  - **The list is "sessions where I am on the team", not "sessions for my
    role"** — a single `or_filters` across `assigned_doctor` /
    `assigned_nurse` / `assigned_driver` in `find_my_schedule`. That removes
    all role branching and is why the same page serves drivers, who had no
    page of their own. Drivers are not a Role; they are Healthcare
    Practitioners with `custom_role = "Clinic Assistant cum Driver"` holding
    the CAD role.
  - **Cancelled sessions are shown, badged "do not travel", not filtered
    out.** The old empty-state card filtered to `status = Planned` and
    `date > today`, so a camp cancelled for a holiday was invisible and
    today's camp was too — the two cases that actually send someone to the
    wrong place.
  - Site/location/unit/vehicle/practitioner are resolved in five bulk queries
    after the session query, never per row.
  - Deliberately not built: map links (no coordinates or address line exists
    anywhere — `Site` holds only a name and a `Bandhu Location`), day-before
    reminders (needs a decision on SMS vs WhatsApp and who pays), and a month
    grid (worse than a list on a phone). The older "Your Upcoming Sessions"
    card still renders in the Doctor/Nurse empty state and now duplicates a
    weaker version of this.
  - Verified: 82 tests (9 new), plus live Playwright at 420px with real
    `priya.doctor` / `rahul.cad` logins — the doctor sees 8 cards including
    the cancelled one, the driver only the 2 he is driving. Page registered
    with `frappe.reload_doc(force=True)`, never a bare `bench migrate`.
  - Dev-site data left in place on purpose so the feature is clickable: two
    Kalamassery sessions now carry Rahul Menon as driver and vehicle
    `cg 17 5566`, and the 24 Aug one is `Cancelled`.
  - Also this session: the bench redis instances (13000/11000) were not
    running at all, which made one session-schedule test fail on a
    `global_search` assertion — environmental, not a code fault. `bench start`
    is now running.
- 2026-08-14: Guided schedule creation. New `page/new_schedule/` wizard
  (Where / When / Who / Check) replaces the 20-field form as the way in: day
  chips instead of a child table, frequency in plain words, a live "next
  dates" panel, a plain-sentence summary, one Create button. The Desk form
  stays for editing.
  - **Saving a schedule now creates its sessions** (`on_update`), gated on
    `enabled` *and* the master switch — a kill switch that stopped only the
    nightly job would be a lie. Six tests that assumed a save created nothing
    were rewritten to the new contract; an all-weekday schedule now inserts
    ~56 sessions inside the save request, which is bounded by the horizon and
    accepted.
  - `find_assignment_clashes` warns when a doctor, nurse or vehicle is already
    committed elsewhere on the generated dates — live in the wizard, orange
    msgprint on the form. Warns, never blocks.
  - The list view's Add button opens the wizard via `listview_settings`
    `primary_action`. `page.set_primary_action` inside `onload` does not
    survive — `ListView.set_primary_action()` runs after `onload` and
    overwrites it.
  - **`<input type="time">` renders blank unless the value is zero-padded**,
    and Frappe hands a Time back as `9:30:00`. Caught live, not by tests —
    the same family as the earlier `9:30:` slice bug. `clock_value()` pads it.
    Treat every Time crossing into the browser as needing formatting.
  - `SCH-00005` turned out to be leaked test residue carrying
    `nowtime()`-shaped planned times (Frappe fills Time fields that way), and
    the wizard's "last used times" default faithfully inherited them. Deleted
    with the walkthrough schedules; only `SCH-00003`/`SCH-00004` remain.
  - Discoverability: the Admin workspace now has **New Schedule** (opens the
    wizard) and **Clinic Schedules** tiles next to Onboard Staff — before
    this, an admin had to search for the doctype by name to reach any of it.
    **`admin.json` was deleted from disk while doing this** — see the
    dashboard entry below for the real cause, which is `reload_doc` on a
    Workspace, not `bench migrate`.
  - Verified: 90 tests, plus a full live Playwright walk of all four steps as
    Administrator — clinic autofilling project and vehicle, chips driving the
    preview, the clash panel appearing, and Create landing on the saved
    schedule with its camps already made.
- 2026-08-14: Admin/director dashboard (CMID requirement 2), built to match
  how BWH's own apps do it rather than inventing a page. Surveyed the org
  first: `buzz` is the only bwhtech app with a dashboard, and it ships stock
  **Number Cards + a Dashboard Chart as `is_standard` JSON inside the app
  module, referenced by a workspace** (Quick Actions band, then Overview).
  No app in bwhtech builds a custom dashboard page, so the empty Dashboard
  workspace was filled in instead.
  - 6 number cards (Camps Running Now / Planned Today / Late To Open / Left
    Open / Patients Seen Today / Cancelled This Month), one weekly bar chart,
    a "Camps: Next 7 Days" quick list, and the schedule shortcuts.
  - **A number card's `dynamic_filters_json` value is `eval`'d as JavaScript**
    (`frappe/public/js/frappe/utils/dashboard_utils.js:217`), so
    `frappe.datetime.now_time()` is a legal filter value. That is the whole
    reason "Camps Late To Open" (date = today, Planned, planned_start_time <
    now) is a card and not a Query Report. `quick_list_filter` goes through
    the same evaluation, so its dates are live expressions — but it must be
    the **array** filter form; a dict silently returns nothing.
  - **`frappe.reload_doc(..., 'workspace', ...)` deletes the workspace JSON
    from disk.** Reproducible, every time, on both `admin` and `dashboard` —
    this replaces the earlier belief that a bare `bench migrate` was the
    culprit and that reload_doc was the safe path. It is safe for the DB
    record only. Generate workspace JSON from a script, and after each reload
    `git checkout -- <file>` and re-run it. Confirm with
    `ls bandhu_app/bandhu_app/workspace | wc -l` (expect 9).
  - Verified live with a purpose-made camp: Planned Today 1, Late To Open 1,
    Left Open 5, quick list populated, no console errors; temp camp deleted
    after. `Camps Left Open` earns its place because this site really has 5
    sessions a nurse never closed.
  - Open: patients-seen-per-camp on one line still needs a Query Report (not
    built). The Dashboard workspace is System Manager only — no Director or
    Programme Manager role exists in this system yet.
- 2026-08-15: Demo data, a gender-list fix, and a doctor-page restyle that was
  reverted.
  - **Staff Onboarding offered seven genders** because `get_form_options` listed
    every record in Frappe's seeded `Gender` master. The CAD patient form has
    always offered three. Now both offer Male / Female / Other, intersected with
    what the master actually holds so the form cannot post a value that fails
    Link validation. Noticed while looking: 8 of 20 practitioners are recorded
    as "Prefer not to say", which nobody plausibly chose — a long list producing
    junk data. Existing records left alone.
  - **Demo data seeded through the real endpoints**, not hand-written rows: a
    camp running today, one Completed yesterday, one Planned for 17 Aug, and six
    patients (`0112600007`–`0112600012`) covering every workflow state. Script in
    the session scratchpad. Two contracts it surfaced —
    `Prescription.medicines` links to **Item** (`PARA500`, not the Medication
    Item title), and `submit_test_results` keys on the child row's `name` with
    `result_type` / `result_value`.
  - **Doctor page restyle: built, shown, reverted at the user's request.** The
    page is back exactly as it was. Reverted edit-by-edit, not with
    `git checkout` — `doctor_form.js` carries uncommitted work from earlier
    sessions, so checking it out would have destroyed that. **Do not
    `git checkout` a page file on this branch until the tree is committed.**
  - The complaints behind that attempt are still true and still unfixed on the
    doctor page: the Age column renders Frappe's `get_age()` as
    `47 Year(s) 6 Month(s) 15 Day(s)` and is three lines tall, site and clinic
    show record ids instead of names, and the 360px `.table-wrap` scroll box
    hides the last patient. If they come up again, fix them as bugs rather than
    as a restyle.
  - Dashboard chart moved from Last Quarter to Last Month: 13 weekly buckets for
    two weeks of data drew eleven zeros and overlapping axis labels.
  - `bench start` and its redis instances (13000/11000) were stopped at the end
    of the session. Start bench before running tests — without those,
    `global_search` raises `ConnectionRefusedError` inside one schedule test and
    it reads like a code fault.
- 2026-08-15: Security/correctness audit and the first round of fixes. A
  read-only agent audit produced `AUDIT_FINDINGS.md` (12 findings). Its top
  finding was real and is fixed; one of its findings was wrong and is corrected
  below.
  - **Stored XSS on the patient card, fixed.** The print format interpolated
    `patient_name` with no escape filter, `register_patient` stores the name as
    free text, and `cad_form.js` writes the rendered card into an `about:blank`
    window that inherits the opener's origin — so a name planted by a CAD ran as
    script in the session of whoever printed the card (doctor, nurse, System
    Manager). Fixed with `| e` on `patient_name`, `mobile` and
    `grouped_clinic_id`. Verified by rendering the real template through a
    `SandboxedEnvironment` with `<img src=x onerror=alert(1)>` as the name.
    Root cause was not a missing rule but a missing fact: the app escapes
    obsessively in JS (~70 `escape_html` sites) and nothing recorded that
    Frappe's Jinja env has autoescape off. That fact is now in the landmine
    section above.
  - **`register_patient` accepted a session in any status.** `create_encounter`
    enforced `In Progress` and registration twenty lines away enforced nothing,
    so a patient could be registered into a Cancelled or not-yet-started camp —
    and the session resolves the LSG/unit codes baked into a permanent, printed
    Clinic ID. Both paths now share `require_running_session`; the duplication
    is what let them drift apart.
  - **Nurse `start_session`/`end_session` had no status or date machine.** A
    closed camp could be reopened and any date's camp marked running today,
    which then feeds every board and the dashboard's "Camps Running Now". Both
    now go through `load_session_for_status_change`.
  - **`sync_to_queue` duplicate-insert race.** `Patient Queue.patient` has a
    unique index; two front desks registering the same patient at once both miss
    the lookup and the loser raises `DuplicateEntryError` — which is a
    `NameError` subclass, **not** a `ValidationError`, so `create_encounter`'s
    existing catch never saw it and the whole registration rolled back. Now
    handled with a savepoint and a re-read.
  - **Audit finding F2 was wrong.** It claimed the workflow transition is
    last-write-wins and silently drops child rows. Frappe's
    `Document.check_if_latest` (`frappe/model/document.py:1015`) compares
    `modified` against the DB on every `doc.save()` and raises
    `TimestampMismatchError` — that is exactly the "Record has changed since
    last read" seen on 2026-08-10. The races fail loudly, not silently. No
    compare-and-swap layer needed.
  - **`custom_encounter_status` is not dead, it is uniformly wrong.** The audit
    said no code writes it. True of app code — but the field's own default fills
    it, so all 35 encounters read `Registered` regardless of their real state,
    including completed ones. Removing it is still right but is now a data-
    dropping schema change needing a patch, so it was left for a decision.
  - 100 tests pass (7 new, covering the register/start/end gates — none of this
    behaviour had any coverage). `bench start` was stopped again at the end of
    the session; MariaDB runs as a system service and stays up regardless.
- 2026-08-16: The three doctor-page display bugs carried over from 2026-08-15 are
  fixed. All three existed identically on the Nurse and CAD pages, so they were
  fixed in all three rather than just the one that was complained about.
  - **Age**: `compact_age` / `attach_compact_age` in `utils/patient.py` replace
    Healthcare's `get_age()` string at the display layer — `52y`, `8mo` for
    infants, `12d` for newborns. Verified against live rows:
    `'52 Year(s) 4 Month(s) 16 Day(s)'` now sends as `'52y'`. The stored
    `patient_age` on the encounter is left alone; only the queue payload changes.
    `attach_compact_age` resolves dob for the whole batch in one query.
  - **Site showed the record id.** `Site` is autonamed `SITE-.####` but the live
    records carry slugged ids (`Kalamassery-Industrial-Worksite-Site`), so staff
    saw the id. `label_sites` in `utils/session.py` now swaps it for `site_name`
    inside `find_active_session` and `find_upcoming_sessions`, matching what
    `find_my_schedule` already did. **Clinic was never broken** — `Clinic` is
    autonamed `field:clinic_name`, so its id already is the readable name.
  - **`max-height:360px` on `.table-wrap`** removed from all three pages; the
    page scrolls instead of a short inner box clipping the last patient.
    `overflow:auto` stays for narrow-screen horizontal scroll.
  - 106 tests pass (6 new: 5 age cases, 1 asserting `find_active_session`
    returns the readable site name). The CSS change is the one part not verified
    in a browser.
- 2026-08-20: First of the eight scope reports — **Bandhu Session Report**
  (`report/bandhu_session_report/`, Script Report). One row per camp for a period:
  date, camp, status, site, LSG, district, project, unit, doctor, nurse, opened /
  closed / hours, patients, new vs repeat, completed, tests ordered vs done,
  medicines prescribed vs dispensed. Filters: period (required), project, LSG,
  site, unit, clinic, status. Summary band + a per-camp bar chart. Shortcut added
  to the Dashboard workspace. The other seven reports should follow this shape.
  - **Roles: System Manager only.** A Script Report runs raw SQL and bypasses
    permissions entirely, so the `roles` table on the Report record is the only
    gate. No Director or Programme Manager role exists yet to add.
  - **This bench is Frappe v16.18.2, not v15** as `AUDIT_FINDINGS.md` states.
  - **The counts had to come from the encounter's child tables, not the doctypes
    that look right.** Nothing in the live clinic loop writes `Test Result`,
    `Bandhu Medication Dispense` or `Referral` — tests live in
    `custom_test_instructions` and medicines in `custom_bandhu_prescription`.
    The rows sitting in those three doctypes are pre-handoff seed data whose
    `encounter` column points at a session id. Joining them looked correct and
    silently returned zero everywhere. Referrals are therefore not a column at
    all until the helpline module exists.
  - **Clinical data bug found by a failing test, fixed at the schema.**
    `Test Instructions.result_type` had no blank first option, so Frappe filled
    every newly ordered test with the first Select value — a malaria test nobody
    had run yet read as **Positive** on every board and in any report. Options now
    start with a blank; `patches/clear_untested_result_types.py` clears the rows
    the old schema mislabelled, and only for encounters still `Awaiting Test` so a
    nurse's real result is never rewritten. 4 live rows corrected.
  - **`reload_doc` on the Dashboard workspace deleted its folder from disk again**,
    exactly as the 2026-08-14 entry warns. Copy the JSON aside before the reload
    and restore it after; `ls workspace | wc -l` back to 9.
  - Verified: 112 tests (6 new), plus live Playwright as Administrator — 17 rows,
    the summary band, the chart, and the Dashboard shortcut landing on the report.
    The first chart draw had unreadable axis labels (full date + site name); labels
    are now `d MMM`.
  - Reviewer standards for this repo are recorded from PR #10 (Rl0007): happy path
    with no `{"success": True}` returns, no explicit `frappe.db.rollback()` in a
    request, `frappe.log_error()` with generic `except Exception as error`, full
    variable names, page CSS in its own file. The current tree already complies.
- 2026-08-20 (same session, continued): reports 2 and 3 — **Bandhu Tests Report**
  and **Bandhu Clinic Report**. Both System Manager only, both shortcut-linked
  from the Dashboard workspace. 123 tests pass (11 new).
  - **Tests Report** is row-per-test: test, result, value, then the patient's
    Clinic ID, name, sex, age group and native state, then site / LSG / district /
    project / unit / doctor / camp / encounter. Filters include a `Pending` result,
    which is the absence of a result and so is filtered in Python rather than SQL.
    This is the report that reads clean only because the `result_type` default was
    fixed earlier today — before that every ordered test would have shown Positive.
  - **Clinic Report** is the aggregate view: one row per Clinic, Project, Unit, LSG
    or Site (a `group_by` filter, validated against a whitelist since it selects a
    field), with camps scheduled / held / cancelled, patients, new vs repeat, per
    camp, tests done, medicines dispensed. Totals reconcile with Session Report.
  - `utils/clinic_stats.py` now holds the four per-camp count queries that Session
    and Clinic Report share. `disable_total` on the "Per Camp" column — Frappe's
    total row sums every numeric column, and a summed average is nonsense.
  - **`age_group()` in `utils/patient.py` uses bands we chose** (0-14, 15-29,
    30-44, 45-59, 60+) because the scope doc names age-group breakdowns without
    defining them. Confirm with CMID; changing the bands later changes every
    historical report.
  - **Frappe's IntegrationTestCase does not isolate rows between tests in a class.**
    Five of six Tests Report tests failed first time because each test saw the
    previous test's camps. Fixed by giving every test its own Site in `setUp` and
    filtering on it. Nothing leaked to the site — the rollback happens, but only
    after the class.
