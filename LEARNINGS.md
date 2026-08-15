# Bandhu App — Engineering Learnings

> Persistent knowledge base. Read this in any new session before touching this
> codebase. It captures the current architecture, the known gaps, and the
> reference architecture (Frappe CRM) we are drawing improvements from.

## 1. What this app is

A **mobile clinic (field health camp) MIS** layered on a live
Frappe + ERPNext + Healthcare install. Module root: `bandhu_app.bandhu_app`.
Operational roles: **CAD** (Front Desk, "Clinic Assistant cum Driver"),
**Doctor**, **Nurse**, **Programme Manager** / `System Manager`.

Operational flow (clinic day):
1. CAD front desk opens a `Bandhu Clinic Session` (the daily camp).
2. CAD registers/adds a patient → creates a `Patient Encounter` +
   `Patient Queue` row.
3. CAD "Send to Doctor" → queue moves `Waiting → With Doctor`.
4. Doctor & Nurse open encounters via their role pages.
5. Patients flow through tests / medicine → completed.

## 2. File map (bandhu_app)

- Operating screens: `bandhu_app/page/{cad_form,doctor_form,nurse_form}/{*.py,*.js,*.json}`.
- Core DocTypes: `doctype/bandhu_clinic_session`, `doctype/patient_queue`,
  `doctype/referral`, `doctype/bandhu_medication_dispense`, `doctype/test_result`,
  plus masters (Clinic, Site, Unit, Bandhu Projects, geography) and children
  (Bandhu Diagnosis, Prescription, Test Instructions, Services Provided, Referral Followup).
- Custom fields on standard doctypes: `bandhu_app/custom/{patient_encounter,patient,healthcare_practitioner,...}.json`.
- Utils: `utils/{patient_encounter.py, custom_bandhu_id.py, patient_qr.py,
  custom_qr_code.py, patient.py, state_districts.py}`.
- `api.py`: `get_patient_by_uid` (QR scan endpoint).
- `hooks.py`: `doc_events` for Patient (bandhu id, QR, BMI) and Patient Encounter
  (validate workflow state). **No scheduler events, no fixtures, no permission hooks.**
- `demo_data.py` (seed), `test_phase1_production_rules.py`,
  `test_demo_data.py` (the only tests).

## 3. Frontend approach (bandhu_app) — CURRENT

- **Pure vanilla JS + jQuery + `frappe.ui.page`, NO Vue/frappe-ui.**
- Each screen builds big HTML template-literal strings and does a full
  `page.main.html(...)` rebuild on every action / refresh.
- Client state = module-level mutable globals (`_cad_session`, `_cad_page`, ...).
- Data via `frappe.call` to the page controller's whitelisted methods.
- No real-time (manual "Refresh" only), no loading/error states on the primary
  calls (risk of stuck `frappe.dom.freeze()`), minimal escaping in some
  template interpolations.

Three screens (CAD / Doctor / Nurse) duplicate heavily: near-identical CSS
blobs, an identical `render_welcome()`, duplicated session start/stop server
methods with different guards/labels, and the parallel-`frappe.call`+done-count
pattern.

## 4. State architecture — THE key problem

State lives in **three parallel enums** that are not aligned and drift:

| Store | Field | Values |
|---|---|---|
| `Patient Queue` | `current_stage` | Waiting, With Doctor, With Nurse (Test), With Nurse (Medicine), Completed |
| `Patient Encounter` | `custom_workflow_state` | Waiting for Doctor, With Doctor, Awaiting Test, Awaiting Doctor Review, Awaiting Medicine, Completed |
| `Patient Encounter` | `custom_encounter_status` | Registered, In Consultation, Completed, Referred (mostly dead) |

- The two real stores are synced in **one place only**: `send_to_doctor`
  (cad_form.py) writes both `current_stage` and `custom_workflow_state`.
- Doctor/Nurse screens only ever read/advance the Encounter enum; they never
  write the Queue. So after "With Doctor" the CAD queue board goes stale.
- Enums don't even match names ("With Nurse (Test)" vs "Awaiting Test").
- `custom_encounter_status` is a redundant/ungoverned third enum.

## 5. Permissions — CURRENT

- Page role gates via `page/*.json` `roles` + controller `_require_*` checks.
- Almost every custom DocType grants CRUD only to `System Manager`; pages write
  with `ignore_permissions=True`, so the real enforcement is controller code.
- **Security gaps:** `cad_form.start_session/close_session` have **no** role check
  (cad_form.py:98-111); `custom_workflow_state` is user-editable at perm0 with
  no transition legality (any Doctor can hop states); `send_to_doctor` doesn't
  validate current stage.
- No `permission_query_conditions` / `has_permission` hooks.

## 6. Known tech debt & weaknesses (bandhu_app)

- **N+1 / multi-query everywhere:** doctor screen fetches patient history per
  patient (doctor_form.js); nurse screen queries child tables per encounter;
  CAD resolves each Patient separately. No batching / `frappe.qb` joins / cache.
- **State divergence** (see §4) — the highest-risk item.
- **Security/permission bypasses** (see §5).
- **Full re-render** on every action; no incremental DOM.
- Stage enums duplicated as string literals across 5+ files (cad_form.py
  `stage_order`, patient_queue.py, patient_encounter.py, nurse_form.py filters,
  demo_data) — silently drift on rename.
- `demo_data.ins()` uses `ignore_links`/`ignore_mandatory`, masking validation.
- Many `Data` fields used where `Link`/`Select` belong → no referential integrity.
- No tests for the 3 page controllers or the workflow transition logic.

## 7. Reference architecture: Frappe CRM (frontend/backend) — WHAT WE LEARN FROM

Cloned at `/tmp/opencode/crm`. Vue 3 + frappe-ui + Pinia + vue-router +
socket.io frontend; `crm/` backend app.

### Frontend patterns worth adopting
- **`frappe-ui` resources as source of truth.** `createDocumentResource`
  (per-doc cache keyed by doctype+docname), `createListResource`,
  `createResource`. Pages don't hand-build DOM.
- **`useDocument` factory** (`frontend/src/data/document.js`): centralizes
  create + save + validation, per-doctype caches (`documentsCache`,
  `controllersCache`, `assigneesCache`, `permissionsCache`), `realtime: true`
  socket reload on `refetch_resource`, toast + mandatory-field error handling,
  `_save.submit` override running client script validation before submit.
- **Thin Pinia stores** (`stores/*`) wrapping resources + module-level refs;
  no heavy duplication of state.
- **`useListResource`** for lists: filtering/group-by/kanban/sort serialized to
  one backend endpoint `crm.api.doc.get_data` (paginated `frappe.get_list`),
  with controller `default_list_data()` defining default columns/rows/kanban.
- **Reusable composables**: `useAttachments`, `useTimelinePreferences`,
  `useActiveTabManager`, `useKeyboardShortcuts`, `useBroadcast`.
- **Lazy-loaded routes**; PWA (vite-plugin-pwa); `import.meta.glob` for doctype scripts.

### Backend patterns worth adopting
- **`permission_query_conditions` + `has_permission`** in
  `crm/permissions/org_hierarchy.py`: builds `frappe.qb` SQL to scope
  owner/subtree + ToDo-assignment reads (safe SQL builder, no raw strings,
  `request_cache`). This is how real row-level permission is enforced.
- **Controller `default_list_data()` / `default_kanban_settings()`** —
  declarative list definitions on the DocType.
- **`@frappe.whitelist()` API methods in `crm/api/*.py`** organized by domain
  (doc, form, activities, comment, todo, assignment_rule, event, views,
  settings, contact) as the contract the frontend calls.
- **Workflow on the DocType** (crm_lead.convert_to_deal): contact + organization
  + deal creation with field mapping (LEAD_DEAL_FIELD_MAP), `db_set` idempotent
  transitions, SLA application (`set_sla`/`apply_sla`).
- **Automation via schedulers** for event/SLA notifications, assignment rules,
  expiry, telemetry; lead syncing via cron.
- **Status change logging** (`crm_status_change_log`) records every transition —
  an audit trail bandhu lacks.

## 8. Prioritized improvement roadmap (highest ROI first)

1. **Single source of truth for workflow state** — NOT DONE (reset). Queue and
   Encounter enums still drift; `sync_to_queue` fix was reverted along with all
   other uncommitted WIP.
2. **Fix permissions & security** — NOT DONE (reset). `start_session`/
   `close_session` have no role check; `validate_workflow_state` transition
   guards were reverted.
3. **Kill N+1** — NOT DONE (reset). Batched lookups were reverted.
4. **Centralize stage enums** — NOT DONE.
5. **Real row-level permissions** — NOT DONE (reset). `utils/permissions.py`
   was reverted.
6. **Add audit trail** — NOT DONE (reset).
7. **Introduce frappe-ui Vue layer for the operating screens** — or at minimum
   extract the three duplicated screens into a shared module. (DX/UX, Major)
8. **Loading/error states + escaping** in the page JS. (UX, Low) — NOT DONE
   (reset). `clinic_ui.js` helper was reverted.

> 2026-08-10: Repo was hard-reset to `upstream/main` (6c50c76) — all prior
> uncommitted WIP for items 1/2/3/5/6/8 above was discarded intentionally.
> Roadmap now reflects the clean repo baseline; rebuild these fixes fresh.
