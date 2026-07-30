# CAD Implementation Reference

Technical documentation for the Clinic Assistant cum Driver (CAD) role implementation in Bandhu App.

---

## Doctype Interactions

```text
Patient ──> Patient Encounter ──> Patient Queue
  │              │
  │              ├── Bandhu Clinic Session
  │              ├── Clinic
  │              ├── Site
  │              └── Project
  │
  └── Healthcare Practitioner (custom_role = "Clinic Assistant cum Driver")
```

### Key Doctypes

| Doctype | Role | CAD Access |
|---|---|---|
| Patient | Master data | Read / Write (limited fields) |
| Patient Encounter | Visit record | Read / Write (vitals only) |
| Patient Queue | Queue management | Read / Write |
| Bandhu Clinic Session | Session container | Read |
| Healthcare Practitioner | Staff record | Reference only |

---

## Custom Fields on Patient Encounter

### CAD-Accessible (permlevel=0)

| Field | Label | Type | Source |
|---|---|---|---|
| `custom_pulse_rate` | Pulse Rate | Data | Manual entry |
| `custom_weight` | Weight | Data | Fetch from Patient |
| `custom_spo2` | SpO2 | Data | Manual entry |
| `custom_height` | Height | Data | Fetch from Patient |
| `custom_blood_pressure` | Blood Pressure | Data | Manual entry |
| `custom_temperature` | Temperature | Data | Manual entry |
| `custom_bmi` | BMI | Data | Calculated |

### CAD-Restricted (permlevel=1)

| Field | Label | Type |
|---|---|---|
| `custom_clinical_findings` | Clinical Findings | Section Break |
| `custom_clinical_findings_notes` | Clinical Findings Notes | Small Text |
| `custom_chief_complaints` | Chief Complaints | Section Break |
| `custom_past_history` | Past History | Small Text |
| `custom_allergy_history` | Allergy History | Small Text |
| `custom_investigation` | Investigation | Section Break |
| `custom_test_instructions` | Test Instructions | Table |
| `custom_diagnosis` | Diagnosis | Section Break |
| `custom_patient_diagnosis` | Patient Diagnosis | Table |
| `custom_advice` | Advice | Section Break |
| `custom_attach_prescription` | Attach Prescription | Attach |
| `custom_other_advisory` | Other Advisory | Small Text |
| `custom_bandhu_prescription` | Prescription | Table |
| `custom_bandhu_services_provided` | Services Provided | Table |

---

## Permission Levels

Permission levels are set via Custom Field `permlevel` property in `patient_encounter.json`:

```json
{
  "fieldname": "custom_clinical_findings_notes",
  "permlevel": 1,
  ...
}
```

DocType-level DocPerm for `bandhu_clinic_session.json`:

```json
{
  "read": 1,
  "role": "Clinic Assistant cum Driver"
}
```

### CAD Frappe Role

**Role Name:** `Clinic Assistant cum Driver`

Assigned to user: `bob@cad.cmid`

---

## Automation & Hooks

### Patient Creation (`hooks.py`)

```python
doc_events = {
    "Patient": {
        "before_insert": "bandhu_app.bandhu_app.utils.custom_bandhu_id.set_bandhu_id",
        "after_insert": "bandhu_app.bandhu_app.utils.patient_qr.create_patient_qr",
        "validate": "bandhu_app.bandhu_app.utils.patient.validate_bmi",
    }
}
```

| Hook | Trigger | Action |
|---|---|---|
| `before_insert` | New Patient | Generates Bandhu ID |
| `after_insert` | New Patient saved | Creates QR code |
| `validate` | Patient save | Calculates BMI from height/weight |

### BMI Calculation (`utils/patient.py`)

```python
def validate_bmi(doc, method):
    h = flt(doc.custom_height_m)
    w = flt(doc.custom_weight_kg)
    if h > 0 and w > 0:
        doc.custom_bmi = round(w / (h * h), 2)
    else:
        doc.custom_bmi = None
```

### Client-Side BMI (`public/js/patient.js`)

```javascript
frappe.ui.form.on("Patient", {
    custom_height_m: function (frm) {
        if (frm.doc.custom_height_m && frm.doc.custom_weight_kg) {
            calculate_bmi(frm);
        }
    },
    custom_weight_kg: function (frm) {
        if (frm.doc.custom_height_m && frm.doc.custom_weight_kg) {
            calculate_bmi(frm);
        }
    },
});
```

---

## Fetch-From Field Mappings

| Encounter Field | Source Field |
|---|---|
| `custom_height` | `patient.custom_height_m` |
| `custom_weight` | `patient.custom_weight_kg` |
| `custom_state` | `custom_location.state` |
| `custom_lsg` | `custom_location.lsg` |

---

## Workflow State

The `custom_workflow_state` field (Link to `Workflow State`, hidden) drives the patient journey:

```text
Registered → Waiting for Doctor → In Consultation → 
  (optional) Nurse Tests → Doctor Review → 
  (optional) Nurse Medicine Dispense → Completed
```

State transitions are managed by custom scripts in:
- `page/doctor_form/doctor_form.js`
- `page/nurse_form/nurse_form.js`

---

## CAD Workspace Configuration

**File:** `workspace/cad/cad.json`

### Quick Lists

| Name | Filter |
|---|---|
| Completed Patients | `custom_workflow_state = "Completed"`, `encounter_date = Today` |

### Shortcuts

| Label | Link To |
|---|---|
| Patients | Patient |
| Vehicle | Vehicle |
| Vehicle Usage Log | Vehicle Usage Log |
| Vehicle Refuel Log | Vehicle Refuel Log |

---

## Doctor Dashboard (Queue View)

**File:** `page/doctor_form/doctor_form.js`

The doctor dashboard renders a patient queue filtered by current Clinic Session. Key features:

- **Scrollable table** with `max-height: 360px` and sticky headers for 100+ patient support
- **Visit history badges** — collapsible date list per patient with expand/collapse chevron
- **Frappe-native CSS** — uses `--page-max-width`, `--padding-md`, `--table-border-color`, `--heading-color`, `--text-sm` design tokens
- **No row hover effect** on queue rows (to avoid conflict with history chips)

### History Badge Behaviour

```javascript
// Each patient row has a grey chip showing visit count
// Clicking the chevron expands to show individual visit dates
// Dates render as inline grey chips with grey background
```

---

## Nurse Dashboard

**File:** `page/nurse_form/nurse_form.js`

Similar structure to doctor dashboard with Frappe-native styling and scrollable queue.

---

## Key Files

| File | Purpose |
|---|---|
| `custom/patient_encounter.json` | Custom fields + permlevels |
| `custom/patient.json` | Patient custom fields (BMI, height, weight) |
| `custom/healthcare_practitioner.json` | `custom_role` select options |
| `doctype/bandhu_clinic_session/bandhu_clinic_session.json` | DocPerm + driver link filter |
| `public/js/patient.js` | Client-side BMI calculator |
| `utils/patient.py` | Server-side BMI validation |
| `utils/custom_bandhu_id.py` | Auto ID generation |
| `utils/patient_qr.py` | QR code generation |
| `page/doctor_form/doctor_form.js` | Doctor queue dashboard |
| `page/nurse_form/nurse_form.js` | Nurse queue dashboard |
| `workspace/cad/cad.json` | CAD workspace layout |
| `hooks.py` | Doc events + doctype JS wiring |
