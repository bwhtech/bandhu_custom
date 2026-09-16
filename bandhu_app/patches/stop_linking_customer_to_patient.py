import frappe


def execute():
	frappe.db.set_single_value("Healthcare Settings", "link_customer_to_patient", 0)
