import frappe

DEFAULT_GENDERS = ["Male", "Female", "Other"]


def execute():
	settings = frappe.get_single("Bandhu Settings")
	if settings.offered_genders:
		return

	for gender in DEFAULT_GENDERS:
		if not frappe.db.exists("Gender", gender):
			frappe.get_doc({"doctype": "Gender", "gender": gender}).insert(ignore_permissions=True)
		settings.append("offered_genders", {"gender": gender})

	settings.save(ignore_permissions=True)
