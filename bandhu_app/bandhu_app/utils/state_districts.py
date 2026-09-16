import frappe

from bandhu_app.bandhu_app.page.cad_form.cad_form import require_cad_access

DISTRICT_LIMIT = 500


@frappe.whitelist()
def get_districts(txt: str = "", state: str | None = None) -> list[str]:
	require_cad_access()

	if not state:
		return []

	filters = {"state": state}
	if txt:
		filters["district_name"] = ("like", f"%{txt}%")

	return frappe.get_list(
		"District",
		filters=filters,
		pluck="district_name",
		order_by="district_name asc",
		limit=DISTRICT_LIMIT,
	)
