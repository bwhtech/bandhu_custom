import frappe
from frappe import _

from bandhu_app.bandhu_app.utils.patient import attach_compact_age

PATIENT_DETAIL_FIELDS = [
	"patient_name",
	"sex",
	"dob",
	"mobile",
	"custom_bandhu_id",
	"custom_abha_id",
	"custom_height_m",
	"custom_weight_kg",
	"custom_bmi",
	"custom_temperature",
	"custom_native_state",
	"custom_native_district",
	"custom_native_country",
	"custom_sector_of_employment",
	"custom_specify_employment_sector",
	"custom_name_of_company",
]

ENCOUNTER_LIST_FIELDS = [
	"name",
	"patient",
	"patient_name",
	"patient_age",
	"patient_sex",
	"encounter_date",
	"custom_workflow_state",
]

ENCOUNTER_CLINICAL_TABLES = {
	"tests": ("Test Instructions", ["name", "test_name", "notes", "result_type", "result_value"]),
	"prescriptions": (
		"Prescription",
		[
			"name",
			"medicines",
			"dosage_frequency",
			"duration_days",
			"quantity",
			"instructions",
			"dispensed",
		],
	),
	"diagnosis": ("Bandhu Diagnosis", ["diagnosis_name", "notes"]),
}


def get_patient_details(patient: str) -> dict:
	if not frappe.db.exists("Patient", patient):
		frappe.throw(_("Patient not found."))
	return frappe.db.get_value("Patient", patient, PATIENT_DETAIL_FIELDS, as_dict=True)


def get_clinical_details_by_encounter(encounter_names: list) -> dict:
	"""Tests, prescriptions and diagnosis for a whole queue in one query per child table.
	Row by row this was three queries a patient, on a camp board a nurse reloads all day."""
	if not encounter_names:
		return {}

	details = {name: {key: [] for key in ENCOUNTER_CLINICAL_TABLES} for name in encounter_names}

	for key, (child_doctype, fields) in ENCOUNTER_CLINICAL_TABLES.items():
		rows = frappe.get_all(
			child_doctype,
			# Prescription rows also hang off Bandhu Medication Dispense, so the parent name
			# alone can pull in another doctype's rows.
			filters={"parent": ["in", encounter_names], "parenttype": "Patient Encounter"},
			fields=["parent", *fields],
			order_by="parent asc, idx asc",
		)
		for row in rows:
			details[row.pop("parent")][key].append(row)

	return details


def get_session_encounters(clinic_session: str, workflow_state) -> list:
	encounters = frappe.get_all(
		"Patient Encounter",
		filters={
			"custom_clinic_session": clinic_session,
			# An encounter created outside the Bandhu forms has no workflow state at all.
			# A bare `!=` would drop it, but frappe wraps the operator in IFNULL — keep it
			# going through the query builder rather than hand-writing the comparison.
			"custom_workflow_state": workflow_state,
		},
		fields=ENCOUNTER_LIST_FIELDS,
		order_by="encounter_date desc, creation desc",
	)

	clinical_details = get_clinical_details_by_encounter([encounter.name for encounter in encounters])
	for encounter in encounters:
		encounter.update(clinical_details[encounter.name])

	return attach_compact_age(encounters)
