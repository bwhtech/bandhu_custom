import frappe
from frappe import _

VALID_WORKFLOW_STATES = {
	"Waiting for Doctor",
	"Awaiting Test",
	"Awaiting Doctor Review",
	"Awaiting Medicine",
	"Completed",
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
