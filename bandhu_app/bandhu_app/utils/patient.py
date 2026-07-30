import frappe
from frappe.utils import flt


def validate_bmi(doc, method):
	h = flt(doc.custom_height_m)
	w = flt(doc.custom_weight_kg)
	if h > 0 and w > 0:
		doc.custom_bmi = round(w / (h * h), 2)
	else:
		doc.custom_bmi = None
