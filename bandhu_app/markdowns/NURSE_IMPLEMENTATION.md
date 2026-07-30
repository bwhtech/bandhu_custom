# Nurse Implementation Reference

Technical documentation for the Nurse role implementation in Bandhu App.

---

## Doctype Interactions

```text
Bandhu Clinic Session ──> Patient Encounter
       │                        │
       │                        ├── Test Instructions (child table)
       │                        └── Prescription (child table)
       │
       └── Nurse Dashboard (page/nurse_form)
```

### Key Doctypes

| Doctype | Role | Nurse Access |
|---|---|---|
| Patient Encounter | Visit record | Read / Write (test results, dispense status) |
| Bandhu Clinic Session | Session container | Read / Write (start/end) |
| Test Instructions | Investigation orders | Read / Write (record results) |
| Bandhu Prescription | Prescribed medicines | Read / Write (mark dispensed) |
| Patient Queue | Queue management | Read |

---

## Nurse Dashboard

**Files:**
- `page/nurse_form/nurse_form.py` — server-side methods
- `page/nurse_form/nurse_form.js` — client-side UI
- `page/nurse_form/nurse_form.json` — page definition (roles: System Manager, Nurse)

### Server-Side API

```python
@frappe.whitelist()
def get_session_status() -> dict:
    """Returns today's session for the logged-in nurse.
    Returns: has_session, session_name, status, clinic, site."""

@frappe.whitelist()
def start_session(session_name: str) -> dict:
    """Sets session status to 'In Progress' and records start_time."""

@frappe.whitelist()
def end_session(session_name: str) -> dict:
    """Sets session status to 'Completed' and records end_time."""

@frappe.whitelist()
def get_patients_for_tests(session_name: str) -> list:
    """Returns encounters with workflow_state = 'Awaiting Test',
    including pending test names."""

@frappe.whitelist()
def get_patients_for_medicines(session_name: str) -> list:
    """Returns encounters with workflow_state = 'Awaiting Medicine',
    including prescribed medicine names."""

@frappe.whitelist()
def get_completed_patients(session_name: str) -> list:
    """Returns encounters with workflow_state = 'Completed'."""
```

### Session Resolution

The nurse's session is resolved by matching the logged-in user's linked Healthcare Practitioner record against today's session with `assigned_nurse`:

```python
def get_session_status():
    practitioner = frappe.db.get_value(
        "Healthcare Practitioner",
        {"user_id": user},
        "name",
    )
    session = frappe.db.get_value(
        "Bandhu Clinic Session",
        {"date": today, "assigned_nurse": practitioner},
        ["name", "status", "start_time", "end_time", "clinic", "site"],
        as_dict=True,
    )
```

### Queue Loading

The dashboard loads three queues in parallel and renders them once all API calls complete:

```javascript
function load_queues(page) {
    var done = 0;
    var data = {};
    function check_done() {
        done++;
        if (done < 3) return;
        // render all three sections
    }
    // Parallel API calls:
    frappe.call({ method: "get_patients_for_tests", ... });
    frappe.call({ method: "get_patients_for_medicines", ... });
    frappe.call({ method: "get_completed_patients", ... });
}
```

### Queue Row Click

Clicking any patient row navigates to the Patient Encounter form:

```javascript
page.main.on("click", ".nurse-queue-row", function () {
    var name = $(this).data("name");
    frappe.set_route("Form", "Patient Encounter", name);
});
```

---

## Workflow States (Nurse Perspective)

| State | Description | Set By |
|---|---|---|
| Awaiting Test | Doctor ordered investigations | Doctor (via Has Tests) |
| Awaiting Medicine | Doctor prescribed medicines | Doctor (via Has Prescription) |
| Awaiting Doctor Review | Tests completed by nurse | Nurse (on saving test results) |
| Completed | All workflows finished | System (after medicine dispensed) |

---

## Child Table: Test Instructions

**File:** `doctype/test_instructions/test_instructions.json`

| Field | Type | Description |
|---|---|---|
| `test_name` | Select | Predefined list of available tests |
| `result_value` | Data | Test result (e.g. "Positive", "132 mg/dL") |
| `result_type` | Select | Qualitative / Quantitative |
| `notes` | Small Text | Nurse remarks |

The doctor creates rows; the nurse fills in results.

---

## Child Table: Prescription

**File:** `doctype/prescription/prescription.json`

| Field | Type | Description |
|---|---|---|
| `medicines` | Link | Linked Medicine item |
| `dosage_frequency` | Select | Dosage schedule |
| `duration_days` | Int | Course duration |
| `quantity` | Int | Quantity dispensed |
| `source` | Select | Internal / External |
| `dispensed` | Check | Marked by nurse when dispensed |
| `dispensed_by` | Link | Practitioner who dispensed |
| `instructions` | Small Text | Usage instructions |

The doctor creates rows with medicines and dosage. The nurse marks `dispensed = 1` and sets `dispensed_by` after dispensing.

---

## Permissions

The nurse has full read/write access to Patient Encounter (no permlevel restrictions). Workflow separation is enforced by the dashboard UI — the nurse navigates to encounters from the queue, and the doctor's clinical fields are visible but not modified per workflow policy (not by permlevel).

### DocPerm on Bandhu Clinic Session

```json
{
    "role": "Nurse",
    "read": 1,
    "write": 1
}
```

---

## Dashboard UI

The nurse dashboard uses Frappe-native CSS design tokens. See the CSS in `nurse_form.js` for the full styling.

Key visual features:
- **Responsive layout** — max-width constrained by `--page-max-width`, mobile breakpoint at 768px
- **Scrollable tables** with `max-height: 360px` and sticky headers
- **Session bar** — displays clinic name, site, and status with colored indicator
- **Empty states** — each queue section shows an icon + message when empty

### Session States

| Dashboard State | Session Status | UI Elements |
|---|---|---|
| Pre-session | Planned | Welcome message, session info, Start Session button |
| Active | In Progress | Welcome, session bar, End Session button, three queue sections |
| Post-session | Completed | Welcome, check icon, "Session completed" message |

---

## Key Files

| File | Purpose |
|---|---|
| `page/nurse_form/nurse_form.py` | Session management + queue API |
| `page/nurse_form/nurse_form.js` | Dashboard UI with three queues and session controls |
| `page/nurse_form/nurse_form.json` | Page definition (role-gated) |
| `doctype/bandhu_clinic_session/bandhu_clinic_session.json` | Session doctype with status workflow |
| `doctype/test_instructions/test_instructions.json` | Test order child table |
| `doctype/prescription/prescription.json` | Prescription child table with dispense tracking |
| `doctype/test_result/test_result.json` | (optional) Test result recording |
