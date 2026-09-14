import frappe
from frappe import _
from frappe.utils import cint, cstr, escape_html, formatdate

from bandhu_app.bandhu_app.utils.patient import compact_age
from bandhu_app.bandhu_app.utils.session import fetch_map

PATIENT_FIELDS = ["name", "patient_name", "custom_bandhu_id", "sex", "dob"]
VITALS = (
	("custom_blood_pressure", "BP"),
	("custom_pulse_rate", "Pulse"),
	("custom_spo2", "SpO2"),
	("custom_temperature", "Temperature"),
	("custom_height", "Height"),
	("custom_weight", "Weight"),
	("custom_bmi", "BMI"),
)
NOTES = (
	("custom_chief_complaints", "Patient Complaints"),
	("custom_past_history", "Past History"),
	("custom_allergy_history", "Allergy History"),
	("custom_clinical_findings_notes", "Clinical Findings"),
	("custom_bandhu_clinical_notes", "Observations and Notes on Examination"),
	("custom_other_advisory", "Other Advisory"),
)
VISIT_FIELDS = [
	"name",
	"encounter_date",
	"practitioner_name",
	"custom_workflow_state",
	*(fieldname for fieldname, label in VITALS),
	*(fieldname for fieldname, label in NOTES),
]


def execute(filters=None):
	filters = frappe._dict(filters or {})

	patient = find_patient(filters.get("clinic_id"))
	visit = find_visit(patient.name, filters.get("visit"))
	return get_columns(), build_rows(visit.name), describe_visit(patient, visit)


def find_patient(clinic_id) -> frappe._dict:
	typed = cstr(clinic_id).replace(" ", "").strip()
	if not typed:
		frappe.throw(_("Enter the patient's Clinic ID."))

	matches = frappe.qb.get_query(
		"Patient",
		fields=PATIENT_FIELDS,
		filters=[["custom_bandhu_id", "=", typed], "or", ["name", "=", typed]],
		limit=2,
	).run(as_dict=True)

	if not matches:
		frappe.throw(_("No patient has Clinic ID {0}.").format(escape_html(typed)))
	return next((patient for patient in matches if patient.custom_bandhu_id == typed), matches[0])


def find_visit(patient: str, visit_name) -> frappe._dict:
	visit_filters = {"patient": patient, "docstatus": ["<", 2]}
	chosen = cstr(visit_name).strip()
	if chosen:
		visit_filters["name"] = chosen

	visits = frappe.get_all(
		"Patient Encounter",
		filters=visit_filters,
		fields=VISIT_FIELDS,
		order_by="encounter_date desc, creation desc",
		limit=1,
	)
	if visits:
		return visits[0]

	if chosen:
		frappe.throw(_("Visit {0} is not one of this patient's visits.").format(escape_html(chosen)))
	frappe.throw(_("This patient has no visits yet."))


def build_rows(visit: str) -> list:
	return [
		*diagnosis_rows(visit),
		*test_rows(visit),
		*medicine_rows(visit),
		*referral_rows(visit),
	]


def diagnosis_rows(visit: str) -> list:
	return [
		{"section": _("Diagnosis"), "item": row.diagnosis_name, "detail": row.notes}
		for row in frappe.get_all(
			"Bandhu Diagnosis",
			filters={"parent": visit, "parenttype": "Patient Encounter"},
			fields=["diagnosis_name", "notes"],
			order_by="idx asc",
		)
		if row.diagnosis_name
	]


def test_rows(visit: str) -> list:
	tests = frappe.get_all(
		"Test Instructions",
		filters={"parent": visit, "parenttype": "Patient Encounter"},
		fields=["test_name", "result_type", "result_value", "notes"],
		order_by="idx asc",
	)
	units = fetch_map("Bandhu Test", {test.test_name for test in tests if test.test_name}, ["unit"])

	rows = []
	for test in tests:
		unit = (units.get(test.test_name) or frappe._dict()).unit
		rows.append(
			{
				"section": _("Test"),
				"item": f"{test.test_name} ({unit})" if unit else test.test_name,
				"result": describe_result(test, unit),
				"detail": test.notes,
			}
		)
	return rows


def describe_result(test, unit) -> str:
	if not test.result_type:
		return _("Pending")
	if test.result_type == "Value":
		return " ".join(part for part in (cstr(test.result_value), cstr(unit)) if part)
	return _(test.result_type)


def medicine_rows(visit: str) -> list:
	prescriptions = frappe.get_all(
		"Prescription",
		filters={"parent": visit, "parenttype": "Patient Encounter"},
		fields=[
			"medicines",
			"dosage_frequency",
			"duration_days",
			"quantity",
			"source",
			"dispensed",
			"instructions",
		],
		order_by="idx asc",
	)
	items = fetch_map(
		"Item",
		{prescription.medicines for prescription in prescriptions if prescription.medicines},
		["item_name"],
	)

	rows = []
	for prescription in prescriptions:
		detail = [
			prescription.dosage_frequency,
			_("{0} days").format(prescription.duration_days) if cint(prescription.duration_days) else None,
			_("Qty {0}").format(prescription.quantity) if cint(prescription.quantity) else None,
			_("Buy outside") if prescription.source == "External" else None,
			prescription.instructions,
		]
		rows.append(
			{
				"section": _("Medicine"),
				"item": (items.get(prescription.medicines) or frappe._dict()).item_name
				or prescription.medicines,
				"detail": ", ".join(cstr(part) for part in detail if part),
				"status": _("Dispensed") if prescription.dispensed else _("Not dispensed"),
			}
		)
	return rows


def referral_rows(visit: str) -> list:
	return [
		{
			"section": _("Referral"),
			"item": referral.referred_to,
			"detail": ", ".join(
				cstr(part)
				for part in (
					referral.reason,
					_("{0} priority").format(referral.priority) if referral.priority else None,
				)
				if part
			),
			"status": referral.status,
		}
		for referral in frappe.get_all(
			"Referral",
			filters={"patient_encounter": visit},
			fields=["referred_to", "reason", "priority", "status"],
			order_by="creation asc",
		)
	]


def describe_visit(patient, visit) -> str:
	patient_details = [
		patient.custom_bandhu_id or patient.name,
		patient.sex,
		compact_age(patient.dob) if patient.dob else None,
	]
	visit_details = [
		formatdate(visit.encounter_date) if visit.encounter_date else None,
		visit.practitioner_name,
		visit.custom_workflow_state,
	]
	vitals = [
		f"{_(label)} {cstr(visit.get(fieldname))}" for fieldname, label in VITALS if visit.get(fieldname)
	]

	lines = [
		"<b>{0}</b> | {1}".format(
			escape_html(patient.patient_name or patient.name),
			escape_html(" | ".join(cstr(detail) for detail in patient_details if detail)),
		),
		escape_html(" | ".join(cstr(detail) for detail in visit_details if detail)),
	]
	if vitals:
		lines.append(escape_html(" | ".join(vitals)))
	lines.extend(
		"<b>{0}:</b> {1}".format(escape_html(_(label)), escape_html(visit.get(fieldname)))
		for fieldname, label in NOTES
		if visit.get(fieldname)
	)
	return "<br>".join(lines)


def get_columns() -> list:
	return [
		{"fieldname": "section", "label": _("Section"), "fieldtype": "Data", "width": 110, "align": "left"},
		{"fieldname": "item", "label": _("Item"), "fieldtype": "Data", "width": 240, "align": "left"},
		{"fieldname": "result", "label": _("Result"), "fieldtype": "Data", "width": 140, "align": "left"},
		{"fieldname": "detail", "label": _("Details"), "fieldtype": "Data", "width": 300, "align": "left"},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 130, "align": "left"},
	]
