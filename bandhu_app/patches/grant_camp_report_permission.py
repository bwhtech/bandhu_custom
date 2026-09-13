import frappe
from frappe.permissions import add_permission, update_permission_property

SESSION_REPORT_ROLES = ("Director", "Programme Manager")


def execute():
	for role in SESSION_REPORT_ROLES:
		if not frappe.db.exists("Role", role):
			continue
		add_permission("Bandhu Clinic Session", role, 0)
		update_permission_property("Bandhu Clinic Session", role, 0, "report", 1)
