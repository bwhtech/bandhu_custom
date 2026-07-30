# Business Rules

This document defines the domain rules that must never be violated. If a code change breaks one of these rules, it is a bug.

---

## 1. Patient Rules

| Rule | Statement |
|---|---|
| 1.1 | A Patient is a unique person and can have multiple Patient Encounters. |
| 1.2 | Every Patient Encounter belongs to exactly one Patient. |
| 1.3 | Patient history is determined using the **Patient** — never the treating Doctor. |
| 1.4 | Existing patients must always be searched before creating a new Patient record to avoid duplicates. Search keys: Patient ID, QR Code, Mobile Number, ABHA ID, Name, DOB. |

---

## 2. Clinic Rules

| Rule | Statement |
|---|---|
| 2.1 | A Clinic represents a mobile clinic unit. |
| 2.2 | A Clinic may be linked to a Project. |
| 2.3 | A Clinic can have multiple Sites. |
| 2.4 | A Site can host many Clinic Sessions across different dates. |
| 2.5 | A Clinic Session belongs to exactly one Clinic and one Site. |

---

## 3. Session Rules

| Rule | Statement |
|---|---|
| 3.1 | Session lifecycle: **Planned → In Progress → Completed**. This is the only valid state transition path. |
| 3.2 | Only one active (In Progress) session should exist for a given Clinic + Site + Date combination. |
| 3.3 | A Completed session cannot be restarted or set back to In Progress. |
| 3.4 | New Patient Encounters cannot be created once a session is Completed. |
| 3.5 | Start Time is automatically recorded when the Nurse starts the session. |
| 3.6 | End Time is automatically recorded when the Nurse ends the session. |
| 3.7 | Every session requires a Date, Clinic, Site, and Project (mandatory fields). |

---

## 4. Staff Rules

| Rule | Statement |
|---|---|
| 4.1 | Doctor cannot start or end sessions. |
| 4.2 | Nurse is the only role that can start and end sessions. |
| 4.3 | CAD registers patients and captures vitals — never clinical data. |
| 4.4 | Doctor performs consultation, diagnosis, and prescription — never registration. |
| 4.5 | Nurse performs investigations and medicine dispensing — never diagnosis. |
| 4.6 | Helpline manages referrals and follow-ups — never clinical workflow. |

---

## 5. Encounter Rules

| Rule | Statement |
|---|---|
| 5.1 | Every Patient Encounter belongs to exactly one Clinic Session. |
| 5.2 | Every Patient Encounter belongs to exactly one Patient. |
| 5.3 | Every Patient Encounter is independent — even for repeat patients, each visit is a new Encounter. |
| 5.4 | Patient history is the collection of all Patient Encounters for that Patient, across all sessions and doctors. |
| 5.5 | An Encounter's date is the visit date, not the date of future follow-ups. |

---

## 6. Workflow Rules

| Rule | Statement |
|---|---|
| 6.1 | Registered patients enter **Waiting for Doctor** state. |
| 6.2 | If Tests are prescribed, workflow moves to **Awaiting Test**. |
| 6.3 | After Tests are completed, workflow moves to **Awaiting Doctor Review**. |
| 6.4 | If Medicines are prescribed, workflow moves to **Awaiting Medicine**. |
| 6.5 | After Medicines are dispensed, workflow moves to **Completed**. |
| 6.6 | If neither Tests nor Medicines are required, workflow moves directly to **Completed**. |
| 6.7 | Workflow state must always reflect the current stage. State transitions must be atomic — no intermediate inconsistent states. |

---

## 7. Queue Rules

| Rule | Statement |
|---|---|
| 7.1 | Queues are **session-specific** — they only show patients from the currently active session. |
| 7.2 | A patient appears only in the queue matching their current workflow state. |
| 7.3 | Completed patients must not appear in active queues (Doctor or Nurse). |
| 7.4 | Queue membership is driven by workflow state on the Encounter — never manually assigned. |
| 7.5 | The Doctor queue shows: Waiting for Doctor + Awaiting Doctor Review states. |
| 7.6 | The Nurse queue has two independent sections: Awaiting Test + Awaiting Medicine. |
| 7.7 | The CAD workspace shows Completed patients only. |

---

## 8. Test Rules

| Rule | Statement |
|---|---|
| 8.1 | If **Has Tests** is checked, at least one Test Instruction row must exist on the Encounter. |
| 8.2 | Test results belong to the Patient Encounter — not to a separate test order record. |
| 8.3 | Completing tests updates the workflow state to **Awaiting Doctor Review**. |
| 8.4 | Patients do not leave the clinic between test order and test completion — the workflow is synchronous within the same visit. |

---

## 9. Prescription Rules

| Rule | Statement |
|---|---|
| 9.1 | If **Has Prescription** is checked, at least one Prescription row must exist. |
| 9.2 | Each Prescription row tracks medicine, dosage, duration, quantity, source (internal/external), and dispense status. |
| 9.3 | A prescription is fulfilled when `dispensed = 1` and `dispensed_by` is set. |
| 9.4 | External source means the patient purchases outside the clinic — no inventory deduction occurs. |
| 9.5 | Medicine dispensing updates the workflow to **Completed**. |

---

## 10. Referral Rules

| Rule | Statement |
|---|---|
| 10.1 | A Referral always originates from a Patient Encounter. |
| 10.2 | A Referral belongs to exactly one Patient. |
| 10.3 | Follow-up logs always belong to one Referral. |
| 10.4 | Referral history is independent of the treating Doctor — referrals are linked to the Patient. |
| 10.5 | Referral status options: Pending → In Progress → Completed → Lost. |
| 10.6 | The Doctor creates referrals; Helpline Staff manages follow-ups. |

---

## 11. Patient History Rules

| Rule | Statement |
|---|---|
| 11.1 | Patient history must include Encounters from **all doctors** across all sessions. |
| 11.2 | History is ordered by Encounter Date descending (newest first). |
| 11.3 | Selecting a history item opens that exact Patient Encounter. |
| 11.4 | History is read-only from the dashboard — cannot be edited or deleted. |

---

## 12. Project Rules

| Rule | Statement |
|---|---|
| 12.1 | A Project represents the funding source. |
| 12.2 | A Project may be linked to a Clinic (long-term association). |
| 12.3 | A Project is always linked to a Clinic Session (mandatory field on session). |
| 12.4 | Reports can be filtered by Project. |

---

## 13. Data Integrity Rules

| Rule | Statement |
|---|---|
| 13.1 | Patient mobile number must be validated for format at entry. |
| 13.2 | ABHA ID must be unique across all Patients if provided. |
| 13.3 | Patient height and weight are the source of truth — Encounter vitals fetch from Patient. |
| 13.4 | BMI is always calculated from height and weight — never entered manually. |
| 13.5 | State and District display conditionally: India → show both; other countries → show Native Country only. |
| 13.6 | District options must filter dynamically based on the selected State. |

---

## 14. Reporting Rules

| Rule | Statement |
|---|---|
| 14.1 | Reports must use completed operational data — never in-flight workflow states. |
| 14.2 | Session Reports aggregate all Encounters for one Clinic Session. |
| 14.3 | Patient History aggregates all Encounters for one Patient across all sessions. |
| 14.4 | Reports must never rely on UI state — they should derive from persisted data only. |
