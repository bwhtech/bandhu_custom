import frappe
from frappe import _

from bandhu_app.bandhu_app.utils.session import find_my_schedule

SCHEDULE_ROLES = {"Doctor", "Nurse", "Clinic Assistant cum Driver", "System Manager"}


def require_schedule_access() -> None:
	if not SCHEDULE_ROLES.intersection(frappe.get_roles()):
		frappe.throw(
			_("You do not have permission to access this page."),
			frappe.PermissionError,
		)


@frappe.whitelist()
def get_my_schedule(days: int | None = None) -> dict:
	require_schedule_access()

	practitioner = frappe.db.get_value(
		"Healthcare Practitioner",
		{"user_id": frappe.session.user},
		"name",
	)
	if not practitioner:
		return {
			"sessions": [],
			"message": _("No Healthcare Practitioner is linked to your account."),
		}

	sessions = find_my_schedule(practitioner, days)
	if not sessions:
		return {
			"sessions": [],
			"message": _("You have no clinic sessions scheduled. Please contact Programme Manager."),
		}

	return {"sessions": sessions}
