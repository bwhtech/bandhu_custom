from datetime import date

import frappe
from frappe import _


def _require_doctor_access() -> None:
	roles = frappe.get_roles()
	if "Doctor" not in roles and "System Manager" not in roles:
		frappe.throw(
			_("You do not have permission to access this page."),
			frappe.PermissionError,
		)


def _get_history(patient: str):
	return frappe.db.get_all(
		"Patient Encounter",
		filters={"patient": patient},
		fields=["name", "encounter_date"],
		order_by="encounter_date desc, creation desc",
	)


def _get_doctor_session():
	today = date.today().isoformat()
	user = frappe.session.user

	practitioner = frappe.db.get_value(
		"Healthcare Practitioner",
		{"user_id": user},
		"name",
	)

	if not practitioner:
		return None

	session = frappe.db.get_value(
		"Bandhu Clinic Session",
		{"date": today, "assigned_doctor": practitioner, "status": ["!=", "Completed"]},
		"name",
	)

	return session


def _get_encounters(session, workflow_state):
	return frappe.db.get_all(
		"Patient Encounter",
		filters={
			"custom_clinic_session": session,
			"custom_workflow_state": workflow_state,
		},
		fields=[
			"name",
			"patient",
			"patient_name",
			"patient_age",
			"patient_sex",
			"encounter_date",
			"custom_workflow_state",
		],
		order_by="encounter_date desc, creation desc",
	)


@frappe.whitelist()
def get_registered_patients():
	_require_doctor_access()
	session = _get_doctor_session()
	if not session:
		return []
	return _get_encounters(session, ["!=", "Completed"])


@frappe.whitelist()
def get_completed_patients():
	_require_doctor_access()
	session = _get_doctor_session()
	if not session:
		return []
	return _get_encounters(session, "Completed")


@frappe.whitelist()
def get_patient_history(patient: str):
	_require_doctor_access()
	if "System Manager" not in frappe.get_roles():
		session = _get_doctor_session()
		if not session:
			return []
		linked = frappe.db.get_value(
			"Patient Encounter",
			{"custom_clinic_session": session, "patient": patient},
			"name",
		)
		if not linked:
			frappe.throw(
				_("You are not permitted to view this patient's history."),
				frappe.PermissionError,
			)
	return _get_history(patient)
