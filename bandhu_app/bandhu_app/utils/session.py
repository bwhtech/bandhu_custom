import frappe

_ACTIVE_STATUS_PRIORITY = ["In Progress", "Planned"]


def find_active_session(practitioner_field: str, practitioner: str) -> dict | None:
	today = frappe.utils.today()
	candidates = frappe.get_all(
		"Bandhu Clinic Session",
		filters={
			"date": today,
			practitioner_field: practitioner,
			"status": ["in", _ACTIVE_STATUS_PRIORITY],
		},
		fields=["name", "status", "clinic", "site", "creation"],
		order_by="creation desc",
	)
	if not candidates:
		return None

	by_status = {row.status: row for row in reversed(candidates)}
	for status in _ACTIVE_STATUS_PRIORITY:
		if status in by_status:
			return by_status[status]
	return None
