# Nurse Module

The Nurse is responsible for clinical support after the doctor's consultation. The nurse starts and ends clinic sessions, performs investigations requested by the doctor, dispenses medicines, provides nursing interventions, and ensures every patient completes the workflow.

The nurse acts as the bridge between diagnosis and treatment, ensuring that every doctor's instruction is completed before the patient exits the clinic.

---

## Responsibilities

- Start and end clinic sessions
- Perform investigations requested by the doctor
- Record investigation results
- Dispense prescribed medicines
- Provide nursing interventions
- Educate patients about medication usage
- Complete the patient workflow

---

## Daily Workflow

### 1. Start Clinic Session

At the beginning of every clinic, the nurse starts the assigned Clinic Session.

Click **Start Session**.

System automatically:
- Changes status to **In Progress**
- Records start time
- Opens patient registration for CAD

Only one active session is allowed per clinic.

### 2. Wait for Patients

The nurse dashboard contains two independent queues:

- **Patients for Tests** — patients waiting for investigations
- **Patients for Medicines** — patients waiting for medicine dispensing

Patients automatically appear in the correct queue based on the doctor's workflow actions.

---

## Test Workflow

### 3. Patient Arrives for Tests

If the doctor requests investigations (enables **Has Tests**), the patient automatically appears in **Patients for Tests**.

The nurse opens the patient encounter. Available information:
- Patient details
- Doctor's test instructions
- Requested test names

### 4. Perform Investigations

The nurse performs each requested investigation.

Each test instruction records:
- Test Name (selected from a predefined list)
- Result Value
- Result Type
- Notes

### 5. Complete Test Results

After all requested investigations are completed, the nurse saves the Test Results.

The patient queue updates automatically — the patient returns to the doctor for review.

---

## Medicine Workflow

### 6. Patient Arrives for Medicines

If the doctor prescribes medicines (enables **Has Prescription**), the patient automatically appears in **Patients for Medicines**.

Available information:
- Prescribed medicines
- Dosage and frequency
- Duration
- Instructions
- Medicine source

### 7. Dispense Medicines

The nurse dispenses each prescribed medicine.

Each prescription row records:
- Medicine (linked item)
- Dosage Frequency
- Duration (days)
- Quantity
- Source (internal / external)
- Instructions
- Dispensed (checkbox)
- Dispensed By (linked practitioner)

#### External Medicines

If medicines are unavailable at the clinic, the doctor may prescribe external medicines. The nurse marks the source as **External**, explains the prescription to the patient, and informs them to purchase outside. No inventory deduction occurs.

### 8. Patient Education

Before discharge, the nurse explains:
- Dosage and timing
- Duration
- Precautions
- Follow-up instructions

### 9. Complete Patient Workflow

Once medicines are dispensed and all required actions completed, the nurse saves the encounter. The system updates the workflow to **Completed**. The patient becomes visible in the CAD Completed Patients list.

---

## End Clinic Session

After all patients are completed, the nurse closes the Clinic Session.

Click **End Session**.

System automatically:
- Changes status to **Completed**
- Records end time
- Locks further patient registrations

No additional patients can be registered after session completion.

---

## Dashboard

The Nurse Dashboard contains three queued sections:

### Patients for Tests

Patients sent by the doctor for investigations. Each row shows the patient name, age, sex, and pending test names.

### Patients for Medicines

Patients whose prescriptions are ready. Each row shows the patient name, age, sex, and prescribed medicine names.

### Completed Patients

Patients whose full workflow is finished.

### Session Controls

| Button | Action |
|---|---|
| Start Session | Begins the clinic day |
| End Session | Closes the clinic day |
| Refresh | Reloads all queues |

The Start button is only shown when the session is in **Planned** status. Once In Progress, the End Session button appears instead.

---

## Permissions

### Can View

- Patient
- Patient Encounter (full clinical fields)
- Doctor's test instructions
- Prescriptions
- Clinic Session
- Patient Queue

### Can Edit

- Test results (result value, result type, notes)
- Medication dispense status (dispensed, dispensed by)
- Nursing interventions
- Clinic Session status (start / end)

### Cannot Edit

The nurse cannot modify:
- Patient registration and demographics
- Chief complaints
- Clinical findings
- Diagnosis
- Clinical advice
- Referral information

These remain under the doctor's responsibility.

---

## Workflow Summary

```
Start Clinic Session
        │
        ▼
  ┌─────┴─────┐
  ▼           ▼
Tests      Medicines
  │           │
  ▼           ▼
Record     Dispense
Results    Medicines
  │           │
  └─────┬─────┘
        ▼
   Patient Education
        │
        ▼
   Completed
        │
        ▼
  End Clinic Session
```

---

## Queue Transitions

```
Doctor sets Has Tests = 1
         │
         ▼
  Patients for Tests (Awaiting Test)
         │
         ▼
  Nurse records test results
         │
         ▼
  Returns to Doctor Queue (Awaiting Doctor Review)
```

```
Doctor sets Has Prescription = 1
         │
         ▼
  Patients for Medicines (Awaiting Medicine)
         │
         ▼
  Nurse dispenses medicines
         │
         ▼
  Completed
```

---

## Notes

- The nurse never creates or edits Patient records.
- The nurse never modifies diagnosis, prescriptions, or clinical findings.
- Patients enter the Nurse Dashboard automatically through workflow transitions initiated by the doctor.
- Clinic Session management (Start / End) is owned by the nurse.
- Test results and medication dispense become permanent parts of the Patient Encounter.
