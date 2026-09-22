import frappe

DRIVER_ROLE = "Clinic Assistant cum Driver"


def is_limited_to_own_sessions(user: str) -> bool:
	roles = frappe.get_roles(user)
	return DRIVER_ROLE in roles and "System Manager" not in roles


def get_practitioner(user: str) -> str | None:
	return frappe.db.get_value("Healthcare Practitioner", {"user_id": user}, "name")


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
	user = user or frappe.session.user
	if not is_limited_to_own_sessions(user):
		return ""

	practitioner = get_practitioner(user)
	if not practitioner:
		return "1=0"

	return (
		f"`tab{doctype}`.clinic_session in (select name from `tabBandhu Clinic Session` "
		f"where assigned_driver = {frappe.db.escape(practitioner)})"
	)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not is_limited_to_own_sessions(user):
		return True

	if not doc.clinic_session:
		return False

	practitioner = get_practitioner(user)
	assigned_driver = frappe.db.get_value("Bandhu Clinic Session", doc.clinic_session, "assigned_driver")
	return bool(practitioner) and assigned_driver == practitioner
