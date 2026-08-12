import frappe

from bandhu_app.bandhu_app.utils.custom_qr_code import generate_qr_code_file


def create_patient_qr(doc, method):
	if doc.custom_qr_code:
		return

	if not doc.custom_bandhu_id:
		return

	file_url = generate_qr_code_file(
		doc=doc,
		# The bare Clinic ID, not a URL. A USB barcode scanner types it straight into the
		# CAD search box, and a phone camera shows a readable ID instead of bouncing the
		# reader into a login page for an API endpoint.
		data=doc.custom_bandhu_id,
		field_name="custom_qr_code",
	)

	frappe.db.set_value(doc.doctype, doc.name, "custom_qr_code", file_url)
