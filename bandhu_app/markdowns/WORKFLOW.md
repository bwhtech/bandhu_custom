# Bandhu Clinic Workflow

End-to-end patient flow across CAD, Doctor, and Nurse roles in a Bandhu Mobile Clinic.

---

## Overview

Every patient visit follows a structured workflow through three roles:

```
CAD ──► Doctor ──► Nurse ──► Complete
```

The workflow is driven by **workflow states** stored on the Patient Encounter. Each role's dashboard filters by these states to show only relevant patients.

---

## Complete Patient Journey

```
                    ┌─────────────────────────────────────┐
                    │        1. Clinic Session             │
                    │    Nurse starts the session          │
                    │    Status → In Progress              │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │        2. Patient Registration       │
                    │    CAD registers patient             │
                    │    Captures demographics + vitals    │
                    │    Creates Patient Encounter         │
                    │    Status: Waiting for Doctor        │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │        3. Doctor Consultation        │
                    │    Doctor reviews patient            │
                    │    Records chief complaints          │
                    │    Clinical findings                 │
                    │    Past / allergy history            │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
    ┌─────────────────────────┐    ┌─────────────────────────┐
    │  4a. Tests Required     │    │  4b. No Tests           │
    │  Doctor sets Has Tests  │    │  Go to Diagnosis        │
    │  Status: Awaiting Test  │    │                         │
    └───────────┬─────────────┘    └───────────┬─────────────┘
                │                             │
                ▼                             ▼
    ┌─────────────────────────┐    ┌─────────────────────────┐
    │  5. Nurse Performs      │    │  6. Doctor Records      │
    │     Investigations      │    │     Diagnosis           │
    │  Records test results   │    │     Advice              │
    │  Status: Awaiting       │    │                         │
    │  Doctor Review          │    └───────────┬─────────────┘
    └───────────┬─────────────┘                │
                │                              │
                ▼                              ▼
    ┌─────────────────────────┐    ┌─────────────────────────┐
    │  Doctor Reviews         │    │  7. Prescription?       │
    │  Results                │    │                         │
    │  Finalizes Diagnosis    │    ├──────┬──────────┬───────┤
    └─────────────────────────┘    │ No   │ Yes      │      │
                                   │      │          │      │
                                   ▼      ▼          │      │
                            ┌────────┐ ┌──────────┐  │      │
                            │Complete│ │Status:   │  │      │
                            │        │ │Awaiting  │  │      │
                            │        │ │Medicine  │  │      │
                            └────────┘ └─────┬────┘  │      │
                                             │       │      │
                                             ▼       │      │
                                    ┌────────────────┘      │
                                    │  8. Nurse Dispenses   │
                                    │      Medicines        │
                                    │  Marks dispensed=1    │
                                    └───────────┬───────────┘
                                                │
                                                ▼
                                    ┌─────────────────────────┐
                                    │  9. Patient Education    │
                                    │  Nurse explains dosage  │
                                    │  Timing, precautions     │
                                    └───────────┬─────────────┘
                                                │
                                                ▼
                                    ┌─────────────────────────┐
                                    │  10. Completed           │
                                    │  Status: Completed       │
                                    │  Visible in CAD workspace│
                                    └─────────────────────────┘
```

---

## Referral Flow (Optional)

At any point during consultation, the doctor can create a referral.

```
Doctor Consultation
        │
        ▼
Doctor enables Has Referral
        │
        ▼
Creates Referral document
   - Pre-filled: Patient, Encounter, Session, Doctor
   - Doctor fills: Reason, Referred To, Priority, Remarks
        │
        ▼
Referral saved ──► Available for Helpline follow-up
```

---

## Workflow States Reference

| State | Description | Visible In |
|---|---|---|
| Waiting for Doctor | Patient registered, awaiting consultation | Doctor Queue |
| Awaiting Test | Doctor ordered investigations | Nurse Queue (Tests) |
| Awaiting Doctor Review | Tests completed, pending doctor review | Doctor Queue |
| Awaiting Medicine | Doctor prescribed medicines | Nurse Queue (Medicines) |
| Completed | All workflow steps finished | CAD Workspace |

---

## Role Handoffs

### CAD → Doctor

```
Trigger: CAD creates Patient Encounter + Queue entry
Result: Patient appears in Doctor Queue
State: Waiting for Doctor
```

### Doctor → Nurse (Tests)

```
Trigger: Doctor sets Has Tests = 1 on encounter
Result: Patient appears in Nurse Test Queue
State: Awaiting Test
```

### Nurse → Doctor (Tests Complete)

```
Trigger: Nurse saves test results on encounter
Result: Patient returns to Doctor Queue
State: Awaiting Doctor Review
```

### Doctor → Nurse (Medicines)

```
Trigger: Doctor sets Has Prescription = 1 on encounter
Result: Patient appears in Nurse Medicine Queue
State: Awaiting Medicine
```

### Nurse → Complete

```
Trigger: Nurse marks medicines as dispensed
Result: Patient appears in CAD Completed list
State: Completed
```

---

## Session Lifecycle

```
Session Created (Planned)
        │
        ▼
Nurse clicks Start Session
        │
        ▼
Session In Progress
   ├── CAD registers patients
   ├── Doctor consults
   ├── Nurse performs tests
   └── Nurse dispenses medicines
        │
        ▼
Nurse clicks End Session
        │
        ▼
Session Completed
   - No further registrations allowed
   - Session stats generated
```

---

## Queue Summary by Role

| Role | Sees | Action |
|---|---|---|
| CAD | Registration form | Register patients, record vitals |
| CAD | Completed Patients list | Verify completion |
| Doctor | Active patients (Waiting for Doctor, Awaiting Doctor Review) | Consult, diagnose, prescribe |
| Nurse | Patients for Tests (Awaiting Test) | Perform investigations |
| Nurse | Patients for Medicines (Awaiting Medicine) | Dispense medicines |
| Nurse | Completed Patients | Verify completion |
| All | Session status | Know current clinic state |

---

## Key Design Decisions

1. **Single Encounter per visit** — all data (registration, vitals, tests, diagnosis, prescription) lives on one Patient Encounter record
2. **State-driven queues** — each role's dashboard filters encounters by `custom_workflow_state` rather than maintaining separate queue tables
3. **No duplicate patient records** — CAD searches existing patients first; only creates new records when no match is found
4. **CAD never sees clinical data** — permlevel=1 on all clinical fields; CAD workspace only shows Completed patients
5. **Nurse session ownership** — only the nurse can start/end the clinic session; CAD and Doctor operate within the active session
