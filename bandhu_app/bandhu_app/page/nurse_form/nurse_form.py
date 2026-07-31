from datetime import date

import frappe


def _require_session_access(session_name: str) -> None:
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if "System Manager" in roles:
		return
	if "Nurse" not in roles:
		frappe.throw(
			"You do not have permission to access this clinic session.",
			frappe.PermissionError,
		)
	practitioner = frappe.db.get_value("Healthcare Practitioner", {"user_id": user}, "name")
	if not practitioner:
		frappe.throw(
			"No Healthcare Practitioner linked to your account.",
			frappe.PermissionError,
		)
	assigned_nurse = frappe.db.get_value("Bandhu Clinic Session", session_name, "assigned_nurse")
	if not assigned_nurse or assigned_nurse != practitioner:
		frappe.throw(
			"You are not assigned to this clinic session.",
			frappe.PermissionError,
		)


@frappe.whitelist()
def get_session_status() -> dict:
	today = date.today().isoformat()
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "Nurse" not in roles:
		return {"has_session": False, "message": "You do not have the Nurse role."}

	practitioner = frappe.db.get_value(
		"Healthcare Practitioner",
		{"user_id": user},
		"name",
	)

	if not practitioner:
		return {"has_session": False, "message": "No Healthcare Practitioner linked to your account."}

	session = frappe.db.get_value(
		"Bandhu Clinic Session",
		{"date": today, "assigned_nurse": practitioner, "status": ["!=", "Completed"]},
		["name", "status", "start_time", "end_time", "clinic", "site"],
		as_dict=True,
	)

	if not session:
		session = frappe.db.get_value(
			"Bandhu Clinic Session",
			{"date": today, "assigned_nurse": practitioner},
			["name", "status", "start_time", "end_time", "clinic", "site"],
			as_dict=True,
		)

	if not session:
		return {
			"has_session": False,
			"message": "No session scheduled for today. Please contact Programme Manager.",
		}

	return {
		"has_session": True,
		"session_name": session.name,
		"status": session.status,
		"clinic": session.clinic,
		"site": session.site,
	}


@frappe.whitelist()
def start_session(session_name: str) -> dict:
	_require_session_access(session_name)
	frappe.db.set_value(
		"Bandhu Clinic Session",
		session_name,
		{"status": "In Progress", "start_time": frappe.utils.now_datetime()},
	)
	return {"success": True}


@frappe.whitelist()
def end_session(session_name: str) -> dict:
	_require_session_access(session_name)
	frappe.db.set_value(
		"Bandhu Clinic Session",
		session_name,
		{"status": "Completed", "end_time": frappe.utils.now_datetime()},
	)
	return {"success": True}


@frappe.whitelist()
def get_patients_for_tests(session_name: str) -> list:
	_require_session_access(session_name)
	encounters = frappe.db.get_all(
		"Patient Encounter",
		filters={"custom_clinic_session": session_name, "custom_workflow_state": "Awaiting Test"},
		fields=[
			"name",
			"patient_name",
			"patient_age",
			"patient_sex",
			"encounter_date",
			"custom_workflow_state",
		],
		order_by="encounter_date desc, creation desc",
	)

	result = []
	for enc in encounters:
		pending_tests = frappe.db.get_all(
			"Test Instructions",
			filters={"parent": enc.name},
			fields=["test_name"],
		)
		result.append(
			{
				"name": enc.name,
				"patient_name": enc.patient_name,
				"patient_age": enc.patient_age,
				"patient_sex": enc.patient_sex,
				"encounter_date": enc.encounter_date,
				"tests": [row.test_name for row in pending_tests],
				"workflow_status": enc.custom_workflow_state,
			}
		)

	return result


@frappe.whitelist()
def get_patients_for_medicines(session_name: str) -> list:
	_require_session_access(session_name)
	encounters = frappe.db.get_all(
		"Patient Encounter",
		filters={"custom_clinic_session": session_name, "custom_workflow_state": "Awaiting Medicine"},
		fields=[
			"name",
			"patient_name",
			"patient_age",
			"patient_sex",
			"encounter_date",
			"custom_workflow_state",
		],
		order_by="encounter_date desc, creation desc",
	)

	result = []
	for enc in encounters:
		prescriptions = frappe.db.get_all(
			"Prescription",
			filters={"parent": enc.name},
			fields=["medicines"],
		)
		result.append(
			{
				"name": enc.name,
				"patient_name": enc.patient_name,
				"patient_age": enc.patient_age,
				"patient_sex": enc.patient_sex,
				"encounter_date": enc.encounter_date,
				"medicines": [row.medicines for row in prescriptions],
				"workflow_status": enc.custom_workflow_state,
			}
		)

	return result


@frappe.whitelist()
def get_completed_patients(session_name: str) -> list:
	_require_session_access(session_name)
	encounters = frappe.db.get_all(
		"Patient Encounter",
		filters={"custom_clinic_session": session_name, "custom_workflow_state": "Completed"},
		fields=[
			"name",
			"patient_name",
			"patient_age",
			"patient_sex",
			"encounter_date",
			"custom_workflow_state",
		],
		order_by="encounter_date desc, creation desc",
	)

	return [
		{
			"name": enc.name,
			"patient_name": enc.patient_name,
			"patient_age": enc.patient_age,
			"patient_sex": enc.patient_sex,
			"encounter_date": enc.encounter_date,
			"workflow_status": enc.custom_workflow_state,
		}
		for enc in encounters
	]
