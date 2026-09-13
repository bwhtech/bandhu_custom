import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

DOCTYPE = "Healthcare Practitioner"
PROPERTY = "show_title_field_in_link"


def execute():
	if frappe.get_meta(DOCTYPE).get(PROPERTY):
		return

	if frappe.db.exists(
		"Property Setter", {"doc_type": DOCTYPE, "property": PROPERTY, "doctype_or_field": "DocType"}
	):
		return

	make_property_setter(DOCTYPE, None, PROPERTY, "1", "Check", for_doctype=True)
	frappe.clear_cache(doctype=DOCTYPE)
