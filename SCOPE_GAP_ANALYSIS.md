# Scope vs. Current Build — Bandhu Mobile Clinics MIS

Source: `Software_for_Bandhu_Mobile_Clinics_of_CMID_Scope_30_March_26.docx`
(client's Scope of Work, 30 Mar 2026). This file compares that document,
section by section, against the code actually in this repo as of
2026-08-12. Status is evidence-based (file paths, doctype fields) — not
verified live in the browser yet. Use the checklist at the end to confirm
each item with the actual app before treating it as done.

Legend: ✅ Done · 🟡 Partial · ❌ Not started

---

## 1. Module-by-module status

| # | Module | Scope requirement | Status | Evidence |
|---|--------|-------------------|--------|----------|
| 1 | Pharmacy | Medicine/consumables purchase, issue, receipt of returns, disposal of expired items; project field | 🟡 Partial | `custom/stock_entry.json` adds `custom_source_project` (Link → Bandhu Projects) on Stock Entry. Uses ERPNext Stock module as-is otherwise — no purchase/receipt/return/disposal workflow specific to Bandhu, no procurement approval chain (see §3 below) |
| 2 | Patient Registration | Touch-friendly Tab form, new + repeat patient, full field list (below) | ✅ Mostly done | `page/cad_form/` (Desk Page, touch-oriented). See §2 field-level table |
| 3 | Doctor | Complaints, observations, test instructions, diagnosis (+category), prescription table, services provided, referral letter + print | ✅ Mostly done | `page/doctor_form/`, `custom/patient_encounter.json` (`custom_bandhu_diagnosis`, `custom_bandhu_prescription`, `custom_bandhu_services_provided`, `custom_test_instructions` — all child tables), `doctype/referral/` |
| 4 | Nurse | Vitals, tests (pos/neg per test type), medicines dispensed, other interventions | ✅ Mostly done | `page/nurse_form/`, `doctype/test_result/`, `doctype/bandhu_medication_dispense/`, vitals fields on `patient_encounter.json` (BP, pulse, temp, SpO2, height, weight, BMI) |
| 5 | Referral (Helpline) | Follow-up log, next follow-up date, auto timestamp+staff name, "pop-up" due-list for helpline | 🟡 Partial | `doctype/referral/`, `doctype/referral_followup/` exist with the right fields (`reason`, `notes`, `priority`, `status`, `helpline_flag`, `required_action_from`). **No dedicated Helpline page/UI** — no `page/referral_form` or similar; unclear if the standard Desk list view is the intended interface or a page was planned. No "pop-up due list" mechanism found (no report, no notification) |
| 6 | Admin | Add/remove user, assign roles, add/remove project, add/remove sites, schedule clinic sessions | 🟡 Partial | `page/staff_onboarding/` (`provision_staff_member` — adds a user + role; no visible remove-user flow). `doctype/bandhu_projects/`, `doctype/site/`, `doctype/unit/` exist as plain masters (add/remove via standard Desk list, not a dedicated form — scope says "leave to consultant" so this may be intentional). `doctype/bandhu_clinic_session/` covers scheduling (date, project, site, times, assigned doctor/nurse/driver, vehicle) |
| 7 | Inventory | Asset management, project field | 🟡 Partial | `custom/asset.json`, `custom/asset_movement.json`, `custom/asset_repair.json` exist (ERPNext Assets module customized). Not verified whether a project field was added the way Stock Entry got one |
| 8 | Dashboard | Reports (tables/charts) by field, for a period, for Managers/Directors | ❌ Not started | `workspace/dashboard/dashboard.json` content is a bare header with no charts, no number cards, no linked reports. Nothing else in the repo builds this |

---

## 2. Patient Registration — field-level check (New Patient)

| Scope field | Status | Notes |
|---|---|---|
| Full Name, DOB, Sex | ✅ | Standard Patient fields |
| Height, Weight | ✅ | `custom_height_m`, `custom_weight_kg` — spec says cm, field is in meters, minor unit mismatch to confirm with the actual form's display label |
| Native State (touch menu) | ✅ | `custom_native_state` (Link → State), CAD form renders as dropdown (fixed 2026-08-11 landmine) |
| Native District (touch menu) | ✅ | `custom_native_district` (Autocomplete) |
| Occupation (touch menu) | 🟡 | Standard `occupation` field exists but is hidden via a property setter (`Patient-occupation-hidden`); `cad_form.py`'s `occupation` parameter writes into `custom_sector_of_employment`, not the `occupation` field — looks like the two scope fields (Occupation vs. Sector of Employment) may have been merged into one. Worth confirming with the client whether that's intentional |
| Sector of Employment (touch menu) | ✅ | `custom_sector_of_employment` (Link → Sectors) |
| Name of Company (dropdown, addable) | ✅ | `custom_name_of_company` |
| Mobile Number | ✅ | Standard `mobile` field |
| ABHA ID | ✅ | `custom_abha_id` |
| Auto: timestamp, date, location, site, LSG, district, unit | 🟡 | Captured on **Patient Encounter** (`custom_location`, `custom_lsg`, `custom_district`, `custom_site`, `custom_project`), not on Patient itself — reasonable, since these are session-scoped, not patient-scoped, but confirm they're actually auto-populated rather than manually entered |
| Unique ID + QR code, sent via WhatsApp | 🟡 | `custom_bandhu_id`, `custom_qr_code` exist and are generated (`utils/custom_bandhu_id.py`, `utils/custom_qr_code.py`). **No WhatsApp send found** — grepped the whole app for "whatsapp", zero hits. QR code is generated and stored, not delivered to the patient |
| Repeat patient search (ABHA/Unique ID/Mobile/DOB/Name/Location/Site/combination) | 🟡 | `cad_form.py` has patient lookup — not yet confirmed which of the 7 search modes are actually wired vs. just name/mobile |

---

## 3. Process flow — coverage

The scope's 24-step daily flow plus 4 sub-flows (Referrals, Follow-up visits,
Helpline follow-up, Programme follow-up, Procurement):

- **Core clinic loop (steps 7–16)**: CAD registers → Doctor examines/orders
  tests or prescribes → Nurse tests/dispenses → back to Doctor → Nurse →
  exit. **Built and tested** (this is the loop rebuilt and repeatedly
  verified across this project's session history — `ALLOWED_TRANSITIONS`
  state machine in `utils/patient_encounter.py`).
- **Repeat visits (FU1–FU3)**: 🟡 dedup on `(patient, session)` exists;
  status per project notes is "backend logic confirmed, not yet
  browser-verified for a genuine same-day repeat visit."
- **Session scheduling / sign-in / medicine intend / vehicle log (steps
  1–6, 17–20)**: 🟡 `bandhu_clinic_session`, `vehicle_usage_log`,
  `vehicle_refuel_log`, `staff_log` doctypes exist with the right fields.
  Whether the actual UI walks a CAD/nurse through these steps in order, or
  they're just background doctypes reachable from a list view, is unverified.
- **Clinic summary + WhatsApp share (steps 17, 21–22)**: ❌ no summary
  report generation or WhatsApp export found.
- **Referral flow (R1–R12)**: 🟡 `referral`/`referral_followup` doctypes
  cover the data model (`helpline_flag`, `required_action_from`,
  `status`); no dedicated Helpline UI or "flag to programme team" workflow
  automation found.
- **Helpline / Programme follow-up pop-up lists (HL1–HL5, PF1–PF3)**: ❌
  not found — no report or notification producing a "due today" list.
- **Procurement (PC1–PC10)**: ❌ not built — this is a multi-step
  approval chain (Pharmacy → Programme Manager → Director Operations →
  procurement → payment) and nothing beyond a single `custom_source_project`
  field on Stock Entry exists for it.

---

## 4. Reports — all 8 named reports

Session, Clinic, Tests, Medicine Utilisation, Patient History, Treatment,
Referral, PHI Report — **none exist as a Frappe Report** (searched for
`"doctype": "Report"` across the whole app, zero matches). The `doctor_form`
UI shows a live patient-history view inline (not a standalone report), but
that's UI, not the reporting layer the scope asks for. This is the single
largest gap against the scope document — module 8 (Dashboard) depends on
these existing.

---

## 5. What to verify next, in order

This is a documentation-only pass — nothing here was tested live. Suggested
order, cheapest/highest-risk first:

1. **Repeat-patient live walkthrough** — confirm FU1–FU3 actually works
   end-to-end in the browser for a genuine same-day second visit, not just
   the backend dedupe check.
2. **Referral module UI** — decide whether Helpline staff get a dedicated
   page (matching CAD/Doctor/Nurse's pattern) or use the standard Desk
   Referral list, and confirm the follow-up-due list exists somewhere.
3. **WhatsApp delivery of Unique ID/QR code** — confirm with the client
   whether this was meant to ship in this phase or was deferred (no
   WhatsApp Business API integration found anywhere in the app or site
   config).
4. **Reports (all 8)** — biggest remaining build item. Needs a decision on
   Frappe Report type per report (Query Report is the natural fit for
   most of these given the "by age group / sex / native state / LSG /
   district / project" breakdown pattern repeated across all 8).
5. **Dashboard** — depends on #4; currently an empty workspace.
6. **Procurement chain (PC1–PC10)** — multi-approver workflow, likely the
   single biggest remaining scope item; confirm with the client whether
   this is in-scope for the current phase or a phase-2 item.
7. **Occupation vs. Sector of Employment field merge** — confirm with the
   client whether collapsing these two scope fields into one was
   intentional.
