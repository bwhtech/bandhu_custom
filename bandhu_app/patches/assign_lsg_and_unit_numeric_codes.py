import frappe

# Assigned once, in the order these locations and units were set up. A code is never
# reused for a different location, because every Clinic ID already issued embeds it.
LSG_NUMERIC_CODES = {
	"Kalamassery-Industrial-Area": "01",
	"Aluva-Market-Cluster": "02",
	"Perumbavoor-Labour-Naka": "03",
}

UNIT_NUMERIC_CODES = {
	"Unit-1-Outreach-Team": "1",
	"Unit-2-Fever-Team": "2",
}


def execute():
	assign_codes("Bandhu Location", "lsg_numeric_code", LSG_NUMERIC_CODES)
	assign_codes("Unit", "unit_numeric_code", UNIT_NUMERIC_CODES)


def assign_codes(doctype: str, fieldname: str, codes: dict[str, str]) -> None:
	for record, code in codes.items():
		if not frappe.db.exists(doctype, record):
			continue

		# Only fill a blank. A code set by hand since this patch was written is the
		# operator's decision and outranks the seed values here.
		if frappe.db.get_value(doctype, record, fieldname):
			continue

		frappe.db.set_value(doctype, record, fieldname, code)
