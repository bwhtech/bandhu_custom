import frappe
from frappe import _

VALID_WORKFLOW_STATES = {
	"Waiting for Doctor",
	"Awaiting Test",
	"Awaiting Doctor Review",
	"Awaiting Medicine",
	"Completed",
}

ALLOWED_TRANSITIONS = {
	"Waiting for Doctor": {"Awaiting Test", "Awaiting Medicine", "Completed"},
	"Awaiting Test": {"Awaiting Doctor Review"},
	"Awaiting Doctor Review": {"Awaiting Medicine", "Completed"},
	"Awaiting Medicine": {"Completed"},
	"Completed": set(),
}

ENCOUNTER_TO_QUEUE_STAGE = {
	"Waiting for Doctor": "Waiting",
	"Awaiting Test": "With Nurse (Test)",
	"Awaiting Doctor Review": "With Doctor",
	"Awaiting Medicine": "With Nurse (Medicine)",
	"Completed": "Completed",
}


def validate_workflow_state(doc, method):
	state = doc.custom_workflow_state
	if not state:
		return

	if state not in VALID_WORKFLOW_STATES:
		frappe.throw(
			_("Invalid workflow state: {0}").format(state),
			frappe.ValidationError,
		)

	if doc.is_new():
		return

	before = doc.get_doc_before_save()
	old_state = before.custom_workflow_state if before else None
	if not old_state or old_state == state:
		return

	if old_state == "Completed":
		frappe.throw(
			_("This encounter is already completed and cannot be reopened."),
			frappe.ValidationError,
		)

	if state not in ALLOWED_TRANSITIONS.get(old_state, set()):
		frappe.throw(
			_("Cannot move patient from {0} to {1} directly.").format(old_state, state),
			frappe.ValidationError,
		)


def sync_to_queue(doc, method):
	stage = ENCOUNTER_TO_QUEUE_STAGE.get(doc.custom_workflow_state)
	if not stage:
		return

	existing = frappe.db.get_value("Patient Queue", {"patient": doc.patient}, "name")
	values = {
		"encounter": doc.name,
		"patient": doc.patient,
		"clinic_session": doc.custom_clinic_session,
		"current_stage": stage,
		"status": "Done" if stage == "Completed" else "Active",
		"last_updated": frappe.utils.now(),
	}
	if stage == "Completed":
		values["completed_on"] = frappe.utils.now()

	if existing:
		frappe.db.set_value("Patient Queue", existing, values)
	else:
		values["created_on"] = frappe.utils.now()
		frappe.get_doc({"doctype": "Patient Queue", **values}).insert(ignore_permissions=True)
