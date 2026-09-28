import frappe

DEFAULT_QUICK_COUNTRIES = ["India", "Nepal"]


def execute():
	settings = frappe.get_single("Bandhu Settings")
	if settings.quick_countries:
		return

	for country in DEFAULT_QUICK_COUNTRIES:
		if frappe.db.exists("Country", country):
			settings.append("quick_countries", {"country": country})

	settings.save(ignore_permissions=True)
