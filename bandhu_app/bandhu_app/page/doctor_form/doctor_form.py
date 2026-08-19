import frappe
from frappe import _

from bandhu_app.bandhu_app.utils.patient import attach_compact_age
from bandhu_app.bandhu_app.utils.patient_details import get_encounter_clinical_details, get_patient_details
from bandhu_app.bandhu_app.utils.session import find_active_session, find_upcoming_sessions

VALID_TEST_NAMES = {"Malaria", "Dengue", "Leptospirosis", "Hb", "GRBS"}


def require_doctor_access() -> None:
	roles = frappe.get_roles()
	if "Doctor" not in roles and "System Manager" not in roles:
		frappe.throw(
			_("You do not have permission to access this page."),
			frappe.PermissionError,
		)


def get_encounter_history(patient: str):
	return frappe.db.get_all(
		"Patient Encounter",
		filters={"patient": patient},
		fields=["name", "encounter_date"],
		order_by="encounter_date desc, creation desc",
	)


def get_doctor_session():
	practitioner = frappe.db.get_value(
		"Healthcare Practitioner",
		{"user_id": frappe.session.user},
		"name",
	)

	if not practitioner:
		return None

	session = find_active_session("assigned_doctor", practitioner)
	return session.name if session else None


@frappe.whitelist()
def get_session_status() -> dict:
	user = frappe.session.user

	roles = frappe.get_roles(user)
	if "Doctor" not in roles and "System Manager" not in roles:
		return {"has_session": False, "message": _("You do not have the Doctor role.")}

	practitioner = frappe.db.get_value(
		"Healthcare Practitioner",
		{"user_id": user},
		"name",
	)

	if not practitioner:
		return {"has_session": False, "message": _("No Healthcare Practitioner linked to your account.")}

	session = find_active_session("assigned_doctor", practitioner)

	if not session:
		return {
			"has_session": False,
			"message": _("No session scheduled for today. Please contact Programme Manager."),
		}

	return {
		"has_session": True,
		"session_name": session.name,
		"status": session.status,
		"clinic": session.clinic,
		"site": session.site,
	}


@frappe.whitelist()
def get_upcoming_sessions() -> list:
	require_doctor_access()
	practitioner = frappe.db.get_value("Healthcare Practitioner", {"user_id": frappe.session.user}, "name")
	if not practitioner:
		return []
	return find_upcoming_sessions("assigned_doctor", practitioner)


def load_owned_encounter(encounter: str):
	doc = frappe.get_doc("Patient Encounter", encounter)
	if "System Manager" not in frappe.get_roles():
		session = get_doctor_session()
		if not session or doc.custom_clinic_session != session:
			frappe.throw(
				_("You are not permitted to update this patient."),
				frappe.PermissionError,
			)
	return doc


def get_encounters_for_state(session, workflow_state):
	encounters = frappe.db.get_all(
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
	for encounter in encounters:
		encounter.update(get_encounter_clinical_details(encounter.name))
	return attach_compact_age(encounters)


@frappe.whitelist()
def get_registered_patients():
	require_doctor_access()
	session = get_doctor_session()
	if not session:
		return []
	return get_encounters_for_state(session, ["!=", "Completed"])


@frappe.whitelist()
def get_completed_patients():
	require_doctor_access()
	session = get_doctor_session()
	if not session:
		return []
	return get_encounters_for_state(session, "Completed")


def verify_patient_linked_to_my_session(patient: str) -> None:
	if "System Manager" in frappe.get_roles():
		return
	session = get_doctor_session()
	if not session:
		frappe.throw(_("You are not permitted to view this patient's details."), frappe.PermissionError)
	linked = frappe.db.get_value(
		"Patient Encounter",
		{"custom_clinic_session": session, "patient": patient},
		"name",
	)
	if not linked:
		frappe.throw(_("You are not permitted to view this patient's details."), frappe.PermissionError)


@frappe.whitelist()
def get_patient_history(patient: str):
	require_doctor_access()
	verify_patient_linked_to_my_session(patient)
	return get_encounter_history(patient)


@frappe.whitelist()
def get_patient_registration_details(encounter: str):
	require_doctor_access()
	doc = load_owned_encounter(encounter)
	return get_patient_details(doc.patient)


@frappe.whitelist()
def order_test(encounter: str, tests: list | str, notes: str | None = None) -> None:
	require_doctor_access()
	tests = frappe.parse_json(tests)

	if not tests:
		frappe.throw(_("Select at least one test."))
	invalid = set(tests) - VALID_TEST_NAMES
	if invalid:
		frappe.throw(_("Unknown test(s): {0}").format(", ".join(invalid)))

	doc = load_owned_encounter(encounter)
	if doc.custom_workflow_state != "Waiting for Doctor":
		frappe.throw(_("Tests can only be ordered for a patient waiting for the doctor."))

	for test_name in tests:
		doc.append("custom_test_instructions", {"test_name": test_name, "notes": notes})

	doc.custom_workflow_state = "Awaiting Test"
	doc.save(ignore_permissions=True)


@frappe.whitelist()
def prescribe_medicine(encounter: str, prescriptions: list | str) -> None:
	require_doctor_access()
	prescriptions = frappe.parse_json(prescriptions)

	if not prescriptions:
		frappe.throw(_("Add at least one medicine."))

	doc = load_owned_encounter(encounter)
	if doc.custom_workflow_state not in ("Waiting for Doctor", "Awaiting Doctor Review"):
		frappe.throw(
			_("Medicine can only be prescribed for a patient waiting for or under doctor review."),
		)

	for row in prescriptions:
		medicine = (row.get("medicines") or "").strip()
		if not medicine:
			frappe.throw(_("Every prescription row needs a medicine."))
		doc.append(
			"custom_bandhu_prescription",
			{
				"medicines": medicine,
				"dosage_frequency": row.get("dosage_frequency"),
				"duration_days": row.get("duration_days"),
				"quantity": row.get("quantity"),
				"instructions": row.get("instructions"),
			},
		)

	doc.custom_workflow_state = "Awaiting Medicine"
	doc.save(ignore_permissions=True)


@frappe.whitelist()
def complete_encounter(
	encounter: str, diagnosis: str | None = None, clinical_notes: str | None = None
) -> None:
	require_doctor_access()

	doc = load_owned_encounter(encounter)
	if doc.custom_workflow_state not in ("Waiting for Doctor", "Awaiting Doctor Review"):
		frappe.throw(
			_("This patient cannot be marked complete from their current state."),
		)

	if diagnosis:
		doc.append("custom_bandhu_diagnosis", {"diagnosis_name": diagnosis})
	if clinical_notes:
		doc.custom_bandhu_clinical_notes = clinical_notes

	doc.custom_workflow_state = "Completed"
	doc.save(ignore_permissions=True)
