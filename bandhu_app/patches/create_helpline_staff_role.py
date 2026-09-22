import frappe

HELPLINE_ROLE = "Helpline Staff"


def execute():
	if frappe.db.exists("Role", HELPLINE_ROLE):
		return

	frappe.get_doc({"doctype": "Role", "role_name": HELPLINE_ROLE, "desk_access": 1}).insert(
		ignore_permissions=True
	)
