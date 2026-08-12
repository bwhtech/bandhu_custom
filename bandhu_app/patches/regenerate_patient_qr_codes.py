import frappe

from bandhu_app.bandhu_app.utils.custom_qr_code import generate_qr_code_file

BATCH_SIZE = 200


def execute():
	"""QR images used to encode an API URL, which scans to a raw JSON page. Re-issue them
	against the bare Clinic ID so a scanner or a phone camera both read something usable."""
	patients = frappe.get_all(
		"Patient",
		filters={"custom_bandhu_id": ["is", "set"]},
		fields=["name", "custom_bandhu_id"],
	)

	for index, patient in enumerate(patients, start=1):
		regenerate_qr_code(patient.name)

		if index % BATCH_SIZE == 0:
			frappe.db.commit()


def regenerate_qr_code(patient_name: str) -> None:
	for file_name in frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Patient",
			"attached_to_name": patient_name,
			"attached_to_field": "custom_qr_code",
		},
		pluck="name",
	):
		frappe.delete_doc("File", file_name, force=True, ignore_permissions=True)

	patient = frappe.get_doc("Patient", patient_name)
	file_url = generate_qr_code_file(doc=patient, data=patient.custom_bandhu_id, field_name="custom_qr_code")
	frappe.db.set_value("Patient", patient_name, "custom_qr_code", file_url, update_modified=False)
