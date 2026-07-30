# Clinic Assistant cum Driver (CAD)

The Clinic Assistant cum Driver (CAD) is the first point of contact for every patient visiting a Bandhu Mobile Clinic. Their responsibility is **patient registration, basic measurements, queue management, and clinic logistics**. The CAD does **not** participate in clinical decision-making.

---

## Responsibilities

- Register new patients
- Identify and register existing patients
- Capture demographic information
- Record basic physical measurements
- Generate patient queue entries
- Manage patient flow to the doctor
- View completed patients
- Assist in clinic logistics

---

## Daily Workflow

### 1. Clinic Session Starts

The nurse starts the clinic session.

Once the session becomes **In Progress**, the CAD can begin registering patients.

Every patient registered belongs to the currently active Clinic Session.

### 2. Register Patient

CAD opens **Patient Registration**.

Two scenarios are possible.

#### New Patient

The CAD creates a new patient record.

Information includes:

- Name
- DOB / Age
- Gender
- Mobile Number
- ABHA ID (optional)
- Height
- Weight
- Temperature
- Native State
- Native District
- Occupation
- Sector of Employment
- Company Name

System automatically:

- Generates Bandhu Patient ID
- Generates QR Code
- Calculates BMI
- Validates phone number
- Validates ABHA uniqueness

#### Existing Patient

CAD searches using any of:

- Patient ID
- QR Code
- Mobile Number
- ABHA ID
- Name
- DOB

Once selected, the patient information is loaded automatically. No duplicate Patient record is created.

### 3. Create Patient Encounter

After registration, CAD creates a new **Patient Encounter** for the active Clinic Session.

The encounter automatically links:

- Patient
- Clinic Session
- Clinic
- Site
- Project
- Date

Basic patient measurements are fetched automatically when available.

### 4. Create Patient Queue Entry

Once the encounter is created, the system automatically creates a **Patient Queue** record.

Initial state:

```
Current Stage: Waiting for Doctor
Status: Active
```

The patient now appears in the Doctor Dashboard. No manual assignment is required.

### 5. Wait During Consultation

CAD performs no action while the doctor and nurse process the patient. Patient movement is handled automatically through workflow states.

### 6. Completed Patients

When the doctor finishes consultation and all required nursing activities are completed, the encounter reaches **Completed**.

Completed patients automatically appear inside the CAD Workspace.

This allows the CAD to:

- Verify completion
- Answer patient queries
- Maintain operational visibility

without accessing clinical notes.

---

## Permissions

### Can View

- Patient
- Patient Encounter (limited fields)
- Clinic Session
- Patient Queue
- Own Workspace

### Can Edit

Patient registration information:

- Demographic details
- Mobile number
- ABHA ID
- Address
- Occupation

Basic measurements:

- Height
- Weight
- Temperature
- Pulse
- Blood Pressure
- SpO₂
- BMI

### Cannot Access

CAD cannot view or modify:

- Clinical Findings
- Chief Complaints
- History
- Allergy History
- Investigations
- Diagnosis
- Clinical Notes
- Advice
- Prescriptions
- Referral Details

These fields are protected using permission levels.

---

## Dashboard

The CAD Workspace contains:

### Patient Registration

Quick access to register patients.

### Existing Patient Search

Fast lookup for repeat patients.

### Completed Patients

Displays patients whose workflow has reached **Completed**.

### Vehicle Operations

Quick shortcuts to:

- Vehicle Usage Log
- Vehicle Refuel Log

---

## Workflow Summary

```text
Clinic Session Started
        │
        ▼
Register New / Existing Patient
        │
        ▼
Create Patient Encounter
        │
        ▼
Create Patient Queue
        │
        ▼
Waiting for Doctor
        │
        ▼
Doctor Consultation
        │
        ▼
(Optional) Nurse Tests
        │
        ▼
Doctor Review
        │
        ▼
Nurse Medicine Dispense
        │
        ▼
Completed
        │
        ▼
Visible in CAD Completed Patients
```
