import frappe


def execute():
	for site in frappe.get_all(
		"Site", fields=["name", "location", "location.lsg as lsg", "location.phcchc as phc_chc"]
	):
		values = {"location": site.location, "lsg": site.lsg, "phc_chc": site.phc_chc}
		for doctype in ("Bandhu Clinic Session", "Bandhu Session Schedule"):
			frappe.db.set_value(doctype, {"site": site.name}, values, update_modified=False)
