from frappe.permissions import add_permission, update_permission_property


def execute():
	add_permission("Patient Encounter", "System Manager", 0)
	update_permission_property("Patient Encounter", "System Manager", 0, "report", 1)
