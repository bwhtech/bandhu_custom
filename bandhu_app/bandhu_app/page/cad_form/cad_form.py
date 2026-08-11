import re

import frappe
from frappe import _
from frappe.utils import flt, validate_phone_number

from bandhu_app.bandhu_app.utils.session import find_active_session


def require_cad_access() -> None:
	roles = frappe.get_roles()
	if "Clinic Assistant cum Driver" not in roles and "System Manager" not in roles:
		frappe.throw(
			_("You do not have permission to access this page."),
			frappe.PermissionError,
		)


def get_cad_practitioner():
	return frappe.db.get_value("Healthcare Practitioner", {"user_id": frappe.session.user}, "name")


def require_session_access(session_name: str) -> None:
	require_cad_access()
	if "System Manager" in frappe.get_roles():
		return
	practitioner = get_cad_practitioner()
	if not practitioner:
		frappe.throw(
			_("No Healthcare Practitioner linked to your account."),
			frappe.PermissionError,
		)
	assigned_driver = frappe.db.get_value("Bandhu Clinic Session", session_name, "assigned_driver")
	if not assigned_driver or assigned_driver != practitioner:
		frappe.throw(
			_("You are not assigned to this clinic session."),
			frappe.PermissionError,
		)


@frappe.whitelist()
def get_session_status() -> dict:
	require_cad_access()

	practitioner = get_cad_practitioner()
	if not practitioner:
		return {"has_session": False, "message": _("No Healthcare Practitioner linked to your account.")}

	session = find_active_session("assigned_driver", practitioner)

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
def get_form_options() -> dict:
	require_cad_access()
	states = frappe.get_all(
		"State",
		fields=["name", "is_major_state"],
		order_by="is_major_state desc, name asc",
	)
	sectors = frappe.get_all("Sectors", fields=["name"], order_by="name asc")
	return {
		"states": [s.name for s in states],
		"sectors": [s.name for s in sectors],
	}


@frappe.whitelist()
def search_patient(query: str) -> list:
	require_cad_access()

	query = (query or "").strip()
	if not query:
		return []

	like = f"%{query}%"
	return frappe.get_all(
		"Patient",
		or_filters=[
			["custom_bandhu_id", "like", like],
			["custom_abha_id", "like", like],
			["mobile", "like", like],
			["patient_name", "like", like],
			["dob", "like", like],
		],
		fields=["name", "patient_name", "custom_bandhu_id", "sex", "dob"],
		limit=20,
	)


@frappe.whitelist()
def register_patient(
	full_name: str,
	dob: str,
	sex: str,
	mobile: str | None = None,
	height_cm: float | None = None,
	weight_kg: float | None = None,
	native_state: str | None = None,
	native_district: str | None = None,
	occupation: str | None = None,
	company_name: str | None = None,
	abha_id: str | None = None,
) -> str:
	require_cad_access()

	full_name = (full_name or "").strip()
	dob = (dob or "").strip()
	sex = (sex or "").strip()

	if not full_name:
		frappe.throw(_("Full name is required."), frappe.ValidationError)
	if not dob:
		frappe.throw(_("Date of birth is required."), frappe.ValidationError)
	if not sex:
		frappe.throw(_("Sex is required."), frappe.ValidationError)

	if height_cm is not None and flt(height_cm) < 0:
		frappe.throw(_("Height cannot be negative."), frappe.ValidationError)
	if weight_kg is not None and flt(weight_kg) < 0:
		frappe.throw(_("Weight cannot be negative."), frappe.ValidationError)

	mobile = (mobile or "").strip() or None
	if mobile:
		validate_phone_number(mobile, throw=True)
		if not re.fullmatch(r"\d{10}", mobile):
			frappe.throw(_("Mobile number must be exactly 10 digits."), frappe.ValidationError)

	name_parts = full_name.split(None, 1)
	first_name = name_parts[0]
	last_name = name_parts[1] if len(name_parts) > 1 else None

	patient_fields = {
		"doctype": "Patient",
		"first_name": first_name,
		"last_name": last_name,
		"sex": sex,
		"dob": dob,
		"mobile": mobile,
		"custom_native_state": native_state or None,
		"custom_native_district": native_district or None,
		"custom_sector_of_employment": occupation or None,
		"custom_name_of_company": company_name or None,
		"custom_abha_id": abha_id or None,
	}
	if height_cm:
		patient_fields["custom_height_m"] = flt(height_cm) / 100
	if weight_kg:
		patient_fields["custom_weight_kg"] = flt(weight_kg)

	try:
		patient = frappe.get_doc(patient_fields)
		patient.insert(ignore_permissions=True)
	except frappe.ValidationError:
		frappe.db.rollback()
		raise

	return patient.name


@frappe.whitelist()
def create_encounter(patient: str, session: str) -> str:
	require_session_access(session)

	if not frappe.db.exists("Patient", patient):
		frappe.throw(_("Patient not found."), frappe.ValidationError)

	session_doc = frappe.db.get_value(
		"Bandhu Clinic Session",
		session,
		["status", "assigned_doctor"],
		as_dict=True,
	)
	if not session_doc:
		frappe.throw(_("Clinic session not found."), frappe.ValidationError)
	if session_doc.status == "Completed":
		frappe.throw(_("This clinic session is already completed."), frappe.ValidationError)
	if session_doc.status != "In Progress":
		frappe.throw(
			_("This clinic session hasn't started yet. Ask the nurse to start the session first."),
			frappe.ValidationError,
		)
	if not session_doc.assigned_doctor:
		frappe.throw(
			_("No doctor is assigned to this clinic session yet. Cannot register patient."),
			frappe.ValidationError,
		)

	existing = frappe.db.get_value(
		"Patient Encounter",
		{
			"patient": patient,
			"custom_clinic_session": session,
			"custom_workflow_state": ["!=", "Completed"],
		},
		"name",
	)
	if existing:
		return existing

	patient_doc = frappe.get_doc("Patient", patient)

	try:
		encounter = frappe.get_doc(
			{
				"doctype": "Patient Encounter",
				"patient": patient,
				"patient_name": patient_doc.patient_name,
				"patient_sex": patient_doc.sex,
				"patient_age": patient_doc.get_age(),
				"practitioner": session_doc.assigned_doctor,
				"custom_clinic_session": session,
				"custom_workflow_state": "Waiting for Doctor",
				"encounter_date": frappe.utils.today(),
			}
		)
		encounter.insert(ignore_permissions=True)
	except frappe.ValidationError:
		frappe.db.rollback()
		raise

	return encounter.name


@frappe.whitelist()
def get_today_queue(session: str) -> list:
	require_session_access(session)

	rows = frappe.get_all(
		"Patient Queue",
		filters={"clinic_session": session},
		fields=["name", "patient", "current_stage", "status"],
		order_by="creation asc",
	)
	if not rows:
		return []

	patient_names = {row.patient for row in rows if row.patient}
	patients = frappe.get_all(
		"Patient",
		filters={"name": ["in", list(patient_names)]},
		fields=["name", "patient_name"],
	)
	name_by_patient = {p.name: p.patient_name for p in patients}

	return [
		{
			"patient": row.patient,
			"patient_name": name_by_patient.get(row.patient, ""),
			"current_stage": row.current_stage,
			"status": row.status,
		}
		for row in rows
	]
