# Doctor Implementation Reference

Technical documentation for the Doctor role implementation in Bandhu App.

---

## Doctype Interactions

```text
Patient Encounter ──> Patient Queue
       │
       ├── Bandhu Clinic Session (assigned_doctor)
       ├── Referral (created by doctor)
       ├── Test Instructions (child table)
       ├── Prescription (child table)
       ├── Patient Diagnosis (child table)
       └── Services Provided (child table)
```

### Key Doctypes

| Doctype | Role | Doctor Access |
|---|---|---|
| Patient Encounter | Visit record | Full read/write |
| Patient Queue | Queue management | Read |
| Bandhu Clinic Session | Session container | Read (via assigned_doctor) |
| Referral | Referral record | Create / Read |
| Test Instructions | Investigation orders | Create / Read |
| Bandhu Prescription | Prescribed medicines | Create / Read |
| Patient Diagnosis | Diagnosed conditions | Create / Read |

---

## Doctor Dashboard

**Files:**
- `page/doctor_form/doctor_form.py` — server-side methods
- `page/doctor_form/doctor_form.js` — client-side UI
- `page/doctor_form/doctor_form.json` — page definition

### Server-Side API

```python
@frappe.whitelist()
def get_registered_patients():
    """Returns active encounters (not Completed) for today's session."""

@frappe.whitelist()
def get_completed_patients():
    """Returns Completed encounters for today's session."""

@frappe.whitelist()
def get_patient_history(patient: str):
    """Returns all previous encounters for a patient (name + encounter_date)."""
```

### Session Resolution

The current session is resolved by matching the logged-in user's linked Healthcare Practitioner record against today's session with `assigned_doctor`:

```python
def _get_doctor_session():
    practitioner = frappe.db.get_value(
        "Healthcare Practitioner",
        {"user_id": user},
        "name",
    )
    session = frappe.db.get_value(
        "Bandhu Clinic Session",
        {
            "date": today,
            "assigned_doctor": practitioner,
            "status": ["!=", "Completed"],
        },
        "name",
    )
```

---

## Workflow States

Workflow states are stored in the `custom_workflow_state` field (Link to `Workflow State`, hidden) on Patient Encounter.

| State | Description | Trigger |
|---|---|---|
| Waiting for Doctor | Initial state after CAD registration | Auto-set on encounter creation |
| Awaiting Test | Doctor ordered tests | Set when `custom_has_tests = 1` |
| Awaiting Medicine | Doctor prescribed medicines | Set when `custom_has_prescription = 1` |
| Awaiting Doctor Review | Tests completed by nurse | Set by nurse after recording results |
| Completed | All workflows finished | Set by doctor or nurse |

These states drive which queue the patient appears in across Doctor, Nurse, and CAD dashboards.

---

## Encounter Fields by Permlevel

### Doctor-Only (permlevel=1)

| Fieldname | Label | Type |
|---|---|---|
| `custom_bandhu_clinical_notes` | Bandhu Clinical Notes | Small Text |
| `custom_chief_complaints` | Chief Complaints | Section Break |
| `custom_past_history` | Past History | Small Text |
| `custom_allergy_history` | Allergy History | Small Text |
| `custom_clinical_findings_notes` | Clinical Findings Notes | Small Text |
| `custom_patient_diagnosis` | Patient Diagnosis | Table (child) |
| `custom_bandhu_diagnosis` | Bandhu Diagnosis | Table (child) |
| `custom_test_instructions` | Test Instructions | Table (child) |
| `custom_bandhu_prescription` | Bandhu Prescription | Table (child) |
| `custom_bandhu_services_provided` | Bandhu Services Provided | Table (child) |
| `custom_attach_prescription` | Attach Prescription | Attach |
| `custom_other_advisory` | Other Advisory | Small Text |
| `custom_has_referral` | Has Referral | Check |

### Shared with CAD (permlevel=0)

| Fieldname | Label | Notes |
|---|---|---|
| `custom_pulse_rate` | Pulse Rate | CAD can enter |
| `custom_weight` | Weight | Fetch from Patient |
| `custom_spo2` | SpO2 | CAD can enter |
| `custom_height` | Height | Fetch from Patient |
| `custom_blood_pressure` | Blood Pressure | CAD can enter |
| `custom_temperature` | Temperature | CAD can enter |
| `custom_bmi` | BMI | Auto-calculated |
| `custom_has_tests` | Has Tests | Doctor toggle |
| `custom_has_prescription` | Has Prescription | Doctor toggle |
| `custom_encounter_status` | Clinic Visit Status | Status display |

---

## Queue Transitions (Doctor Perspective)

```text
                    ┌──────────────────────────────────────────────────┐
                    │                                                  │
                    ▼                                                  │
Doctor Queue (Waiting for Doctor / Awaiting Doctor Review)            │
    │                                                                  │
    ▼                                                                  │
Open Encounter                                                         │
    │                                                                  │
    ▼                                                                  │
Has Tests = 1 ─────► Workflow: Awaiting Test ──► Nurse Queue          │
    │                                          │                       │
    │                                          ▼                       │
    │                                     Tests Completed              │
    │                                          │                       │
    └──────────────────◄── Awaiting Doctor Review ◄──┘                 │
                           │                                           │
                           ▼                                           │
                      Diagnosis                                        │
                           │                                           │
                           ▼                                           │
                    Has Prescription = 1 ──► Workflow: Awaiting Medicine
                           │                                           │
                           ▼                                           │
                      Completed ───────────────────────────────────────┘
```

---

## Referral Creation

Referrals are created directly from the Patient Encounter. The Referral doctype pre-fills:

- **Patient** — from encounter
- **Patient Encounter** — current encounter
- **Clinic Session** — from encounter
- **Project** — from encounter
- **Referral By (Source)** — auto-set to encounter source

Doctor fills:

- **Referred To** — facility name (free text)
- **Referred To Practitioner** — Link to Healthcare Practitioner
- **Reason** — clinical reason for referral
- **Priority** — Low / Medium / High
- **Required Action From** — None / Programme / Clinic
- **Notes** — additional instructions

Referral status options: Pending → In Progress → Completed → Lost

---

## Key Files

| File | Purpose |
|---|---|
| `page/doctor_form/doctor_form.py` | Doctor queue API (session, patients, history) |
| `page/doctor_form/doctor_form.js` | Doctor dashboard UI with queue rendering |
| `page/doctor_form/doctor_form.json` | Page definition |
| `custom/patient_encounter.json` | All encounter custom fields + permlevels |
| `doctype/bandhu_clinic_session/bandhu_clinic_session.json` | Session DocPerm |
| `doctype/referral/referral.json` | Referral doctype definition |
| `doctype/referral/referral.py` | Referral controller |
