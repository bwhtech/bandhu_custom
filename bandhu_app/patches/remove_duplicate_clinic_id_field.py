import frappe


def execute():
	field_name = "Patient-custom_clinic_id"

	frappe.clear_cache(doctype="Patient")
	column_exists = frappe.db.has_column("Patient", "custom_clinic_id")

	if column_exists and frappe.db.count("Patient", {"custom_clinic_id": ["is", "set"]}):
		frappe.log_error(title="custom_clinic_id holds data; not removed")
		return

	if frappe.db.exists("Custom Field", field_name):
		frappe.delete_doc("Custom Field", field_name, ignore_permissions=True)

	if column_exists:
		frappe.db.sql_ddl("alter table `tabPatient` drop column `custom_clinic_id`")
		frappe.clear_cache(doctype="Patient")
