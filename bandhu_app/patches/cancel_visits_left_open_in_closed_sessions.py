import frappe

from bandhu_app.bandhu_app.page.nurse_form.nurse_form import OPEN_VISIT_STATES, cancel_open_visits


def execute():
	closed_sessions = frappe.get_all("Bandhu Clinic Session", filters={"status": "Completed"}, pluck="name")
	if not closed_sessions:
		return

	sessions_with_open_visits = set(
		frappe.get_all(
			"Patient Encounter",
			filters={
				"custom_clinic_session": ["in", closed_sessions],
				"custom_workflow_state": ["in", OPEN_VISIT_STATES],
			},
			pluck="custom_clinic_session",
		)
	)
	for session in sessions_with_open_visits:
		cancel_open_visits(session)
