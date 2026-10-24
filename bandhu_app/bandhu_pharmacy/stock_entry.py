import frappe
from frappe import _

RECEIPT_PURPOSE = "Material Receipt"
CLINIC_ISSUE_PURPOSES = ("Material Issue", "Material Transfer")


def validate_funding_source_and_clinic(doc, method=None):
	if doc.purpose != RECEIPT_PURPOSE:
		doc.custom_funding_source = None
	if doc.purpose not in CLINIC_ISSUE_PURPOSES:
		doc.custom_issued_to_clinic = None

	if doc.purpose == RECEIPT_PURPOSE and not doc.custom_funding_source:
		frappe.throw(_("Funding Source is required for a Material Receipt."), frappe.MandatoryError)
