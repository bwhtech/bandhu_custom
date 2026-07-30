# Permissions Reference

Complete permission matrix across all roles and doctypes in Bandhu App.

---

## Role Definitions

| Role | Short Name | Description |
|---|---|---|
| Clinic Assistant cum Driver | CAD | Patient registration, vitals, logistics |
| Doctor | Doctor | Clinical assessment, diagnosis, prescription |
| Nurse | Nurse | Investigations, medicine dispensing, session management |
| Helpline Staff | Helpline | Referral follow-up and patient support |
| System Manager | Admin | Full system access |

The Frappe roles are defined in the system and assigned to users. The `custom_role` select field on Healthcare Practitioner maps practitioners to their function.

---

## Permission Levels on Patient Encounter

Patient Encounter uses Frappe's permission level system (`permlevel`) to restrict field access by role.

### Level 0 — CAD Accessible

All roles (CAD, Doctor, Nurse) can read and write these fields.

| Field | Label | Type | Notes |
|---|---|---|---|
| `custom_pulse_rate` | Pulse Rate | Data | |
| `custom_weight` | Weight | Data | Fetch from Patient |
| `custom_spo2` | SpO2 | Data | |
| `custom_height` | Height | Data | Fetch from Patient |
| `custom_blood_pressure` | Blood Pressure | Data | |
| `custom_temperature` | Temperature | Data | |
| `custom_bmi` | BMI | Data | Auto-calculated |
| `custom_clinic_session` | Clinic Session | Link | |
| `custom_project` | Project | Data | |
| `custom_encounter_status` | Clinic Visit Status | Select | |
| `custom_site` | Site | Data | |
| `custom_location` | Location | Link | |
| `custom_lsg` | LSG | Data | Read-only |
| `custom_district` | District | Data | Read-only |
| `custom_state` | State | Data | Read-only |
| `custom_has_tests` | Has Tests | Check | Doctor toggle |
| `custom_has_prescription` | Has Prescription | Check | Doctor toggle |
| `custom_bandhu_diagnosis` | Bandhu Diagnosis | Table | |

### Level 1 — Doctor and Nurse Only

These fields are hidden from CAD. Doctor and Nurse have full access.

| Field | Label | Type |
|---|---|---|
| `custom_bandhu_clinical_notes` | Bandhu Clinical Notes | Small Text |
| `custom_chief_complaints` | Chief Complaints | Section Break |
| `custom_past_history` | Past History | Small Text |
| `custom_allergy_history` | Allergy History | Small Text |
| `custom_clinical_findings_notes` | Clinical Findings Notes | Small Text |
| `custom_patient_diagnosis` | Patient Diagnosis | Table (child) |
| `custom_test_instructions` | Test Instructions | Table (child) |
| `custom_bandhu_prescription` | Bandhu Prescription | Table (child) |
| `custom_bandhu_services_provided` | Bandhu Services Provided | Table (child) |
| `custom_attach_prescription` | Attach Prescription | Attach |
| `custom_other_advisory` | Other Advisory | Small Text |
| `custom_has_referral` | Has Referral | Check |

---

## DocType-Level Permissions (Bandhu Doctypes)

Permissions defined in each custom doctype's JSON file.

### Bandhu Clinic Session

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| System Manager | ✅ | ✅ | ✅ | ✅ |
| Doctor | ✅ | ❌ | ❌ | ❌ |
| Nurse | ✅ | ❌ | ❌ | ❌ |
| Clinic Assistant cum Driver | ✅ | ❌ | ❌ | ❌ |

*Note: Nurse has write access via `start_session()` / `end_session()` API methods, not direct DocPerm.*

### Patient Queue

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| System Manager | ✅ | ✅ | ❌ | ❌ |

### Other Bandhu Doctypes (Referral, Vehicle Logs, Staff Log, Unit, Location, Projects)

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| System Manager | ✅ | ✅ | ✅ | ❌ |

*These doctypes are System Manager only by default. Access for specific roles is managed through Frappe's Permission Manager or custom API methods.*

---

## Page-Level Permissions

Custom pages are role-gated in their JSON definition.

### Doctor Dashboard (`page/doctor_form`)

| Role | Access |
|---|---|
| System Manager | ✅ |
| Doctor | ✅ |

### Nurse Dashboard (`page/nurse_form`)

| Role | Access |
|---|---|
| System Manager | ✅ |
| Nurse | ✅ |

---

## Workspace Permissions

### CAD Workspace (`workspace/cad`)

No explicit roles defined — workspace is public. Content is filtered by workflow state.

| Feature | Visibility |
|---|---|
| Completed Patients quick list | Shows only encounters with `custom_workflow_state = "Completed"` for today |
| Vehicle shortcuts | Open to all users with access to the linked doctypes |

---

## Healthcare Doctype Permissions

Patient and Patient Encounter doctypes are owned by the Healthcare app. Their base DocPerm is managed by Healthcare. Bandhu App extends them with:

- **Custom fields** with permlevel restrictions (see Level 0 / Level 1 above)
- **Custom dashboard pages** that filter by workflow state
- **No modification** to Healthcare's native DocPerm

The default Healthcare permissions apply:

| Role | Patient | Patient Encounter |
|---|---|---|
| Doctor | Read / Write | Read / Write |
| Nurse | Read | Read / Write |
| Clinic Assistant cum Driver | Read / Write | Read (limited by permlevel) |

---

## API Method Access

| Method | Called By | Access |
|---|---|---|
| `doctor_form.get_registered_patients` | Doctor Dashboard | Session-based (logged-in doctor's session) |
| `doctor_form.get_completed_patients` | Doctor Dashboard | Session-based |
| `doctor_form.get_patient_history` | Doctor Dashboard | Any authenticated user |
| `nurse_form.get_session_status` | Nurse Dashboard | Nurse role check |
| `nurse_form.start_session` | Nurse Dashboard | Nurse only |
| `nurse_form.end_session` | Nurse Dashboard | Nurse only |
| `nurse_form.get_patients_for_tests` | Nurse Dashboard | Session-based |
| `nurse_form.get_patients_for_medicines` | Nurse Dashboard | Session-based |
| `nurse_form.get_completed_patients` | Nurse Dashboard | Session-based |

---

## Automation Hooks (System-Level)

These run regardless of user permissions:

| Hook | Doctype | Event | Action |
|---|---|---|---|
| `set_bandhu_id` | Patient | `before_insert` | Generates unique Bandhu ID |
| `create_patient_qr` | Patient | `after_insert` | Creates QR code document |
| `validate_bmi` | Patient | `validate` | Calculates BMI from height/weight |

---

## Quick Reference: Who Can Do What

| Action | CAD | Doctor | Nurse | Admin |
|---|---|---|---|---|
| Register new patient | ✅ | ❌ | ❌ | ✅ |
| Record vitals | ✅ | ✅ | ✅ | ✅ |
| Record chief complaints | ❌ | ✅ | ✅ | ✅ |
| Order tests | ❌ | ✅ | ❌ | ✅ |
| Record test results | ❌ | ✅ | ✅ | ✅ |
| Record diagnosis | ❌ | ✅ | ❌ | ✅ |
| Prescribe medicines | ❌ | ✅ | ❌ | ✅ |
| Dispense medicines | ❌ | ❌ | ✅ | ✅ |
| Create referral | ❌ | ✅ | ❌ | ✅ |
| Start/end session | ❌ | ❌ | ✅ | ✅ |
| View completed patients | ✅ | ✅ | ✅ | ✅ |
| View clinical notes | ❌ | ✅ | ✅ | ✅ |
