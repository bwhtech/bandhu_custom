# Doctor Module

The Doctor is responsible for the complete clinical assessment of the patient. The doctor reviews patient information collected during registration, performs the consultation, orders investigations if required, records diagnosis, prescribes medicines, provides medical advice, and initiates referrals when advanced care is needed.

The doctor is the central decision-maker of the entire clinic workflow.

---

## Responsibilities

- Consult patients
- Review patient demographics and previous visit history
- Record chief complaints
- Record clinical findings
- Document history
- Order investigations
- Record diagnosis
- Prescribe medicines
- Recommend services provided
- Generate referrals
- Complete the encounter

---

## Daily Workflow

### 1. Patient Appears in Doctor Queue

After CAD registers a patient, the patient automatically appears in the Doctor Dashboard queue with initial state **Waiting for Doctor**.

The doctor opens the patient encounter from the queue.

### 2. Start Consultation

Opening the patient loads the Patient Encounter with the following information already available:

- Patient ID, Name, Age, Gender, Mobile Number, ABHA ID
- Previous visit count and visit history
- Height, Weight, BMI, Vitals (if recorded by CAD)
- Clinic Session, Clinic, Site, Project

The doctor does not edit patient registration details.

### 3. Clinical Assessment

The doctor records the following clinical information:

- **Chief Complaints** — primary symptoms (e.g. Fever, Headache, Cough)
- **Clinical Findings** — examination observations (e.g. Mild dehydration, Chest congestion)
- **Past History** — relevant previous illnesses (e.g. Diabetes, Hypertension)
- **Allergy History** — known allergies (e.g. Penicillin, Dust)

### 4. Decide Next Clinical Action

#### Option A: No Investigations

Continue directly to diagnosis.

#### Option B: Investigations Required

Doctor enables **Has Tests** and adds one or more **Test Instructions** (e.g. Malaria, Blood Sugar, Hemoglobin).

On save, the encounter workflow changes to **Awaiting Test**. The patient disappears from the Doctor Queue and appears in the Nurse Dashboard under **Patients for Tests**.

The doctor waits until the nurse completes all investigations.

### 5. Nurse Completes Tests

The nurse performs investigations and records results. Workflow changes to **Awaiting Doctor Review**. The patient returns to the Doctor Queue.

### 6. Review Investigation Results

Doctor opens the encounter, reviews requested tests, test results, and nurse remarks, then finalizes diagnosis.

### 7. Diagnosis

Doctor records one or more diagnoses. Diagnosis becomes part of the patient's permanent medical history.

### 8. Advice

Doctor records medical advice (e.g. Drink plenty of fluids, Return after five days).

### 9. Prescription

If medicines are required, doctor enables **Has Prescription** and adds medicines to the prescription table. Each row contains: Medicine, Dosage, Frequency, Duration, Instructions.

On save, workflow changes to **Awaiting Medicine**. The patient appears in the Nurse Dashboard under **Patients for Medicines**.

### 10. Services Provided

Doctor records additional services (e.g. Dressing, Nebulization, Counseling).

### 11. Referral (Optional)

If advanced treatment is required, doctor enables **Has Referral** and clicks **Create Referral**. The Referral document opens with patient, encounter, session, and doctor pre-filled. Doctor fills: Reason, Referred To, Priority, Remarks.

On save, the referral becomes available for follow-up.

### 12. Complete Consultation

Once all required work is completed, the doctor saves the encounter.

Possible outcomes:

- **Tests required** → Nurse Queue (Awaiting Test)
- **Medicines required** → Nurse Queue (Awaiting Medicine)
- **Nothing pending** → Workflow becomes **Completed**. Patient visible in CAD Completed Patients workspace.

---

## Workflow Summary

```
Patient Queue (Waiting for Doctor)
        │
        ▼
Open Encounter
        │
        ▼
Clinical Assessment
        │
        ├── Has Tests? ──► Nurse (Tests) ──► Review Results ──┐
        │                                                     │
        └─────────────────► Diagnosis ◄───────────────────────┘
                                   │
                                   ▼
                              Advice
                                   │
                                   ▼
                            Has Prescription?
                           │                 │
                          Yes               No
                           │                 │
                           ▼                 ▼
                    Nurse (Medicine)    Complete
                           │
                           ▼
                      Completed
```

Referral flow runs independently — the doctor can create a referral at any point during the encounter.

---

## Dashboard

The Doctor Dashboard displays:

- **Patient Queue** — patients waiting for consultation, showing name, age, sex, and visit history
- **Visit History Badges** — expandable badges show first-visit or repeat-patient status with previous encounter dates
- **Refresh** — manual queue refresh

### Queue Columns

| Column | Description |
|---|---|
| Patient Name | Name from Patient record |
| Age | Patient age |
| Sex | Patient gender |
| History | First Visit / Repeat badge with expandable date list |

---

## Permissions

### Can View

- Patient
- Patient Encounter (all fields)
- Patient Queue
- Clinic Session
- Test Results
- Patient History (previous encounters)

### Can Edit

- Chief Complaints
- Clinical Findings
- Past History
- Allergy History
- Diagnosis
- Advice
- Test Instructions
- Prescriptions
- Services Provided
- Referral Information
- Workflow State

### Cannot Edit

- Patient registration details (name, DOB, mobile, address)
- Clinic Session metadata
- Vehicle information
