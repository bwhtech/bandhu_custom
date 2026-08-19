import frappe
from frappe import _

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


def get_patient_details(patient: str) -> dict:
	if not frappe.db.exists("Patient", patient):
		frappe.throw(_("Patient not found."))
	return frappe.db.get_value("Patient", patient, PATIENT_DETAIL_FIELDS, as_dict=True)


def get_encounter_clinical_details(encounter_name: str) -> dict:
	return {
		"tests": frappe.get_all(
			"Test Instructions",
			filters={"parent": encounter_name},
			fields=["name", "test_name", "notes", "result_type", "result_value"],
			order_by="idx asc",
		),
		"prescriptions": frappe.get_all(
			"Prescription",
			filters={"parent": encounter_name},
			fields=[
				"name",
				"medicines",
				"dosage_frequency",
				"duration_days",
				"quantity",
				"instructions",
				"dispensed",
			],
			order_by="idx asc",
		),
		"diagnosis": frappe.get_all(
			"Bandhu Diagnosis",
			filters={"parent": encounter_name},
			fields=["diagnosis_name", "notes"],
			order_by="idx asc",
		),
	}
