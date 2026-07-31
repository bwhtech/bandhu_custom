# bandhu_app/bandhu_app/api.py

import frappe
from frappe import _


@frappe.whitelist()
def get_patient_by_uid(uid: str):
	roles = frappe.get_roles()
	if "Clinic Assistant cum Driver" not in roles and "System Manager" not in roles:
		frappe.throw(
			_("You do not have permission to look up patients."),
			frappe.PermissionError,
		)
	patient = frappe.get_all("Patient", filters={"custom_bandhu_id": uid}, fields=["name", "patient_name"])

	if not patient:
		return {"error": _("Patient not found")}

	return patient[0]
