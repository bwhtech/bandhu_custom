import frappe
from frappe.utils import flt, getdate, today


def compact_age(dob) -> str:
	# Healthcare's own get_age() returns "47 Year(s) 6 Month(s) 15 Day(s)", which wraps to
	# three lines in a queue row. Infants still need months and days to be clinically useful.
	if not dob:
		return ""

	dob = getdate(dob)
	reference = getdate(today())
	if dob > reference:
		return ""

	years = reference.year - dob.year - ((reference.month, reference.day) < (dob.month, dob.day))
	if years >= 1:
		return f"{years}y"

	months = (reference.year - dob.year) * 12 + reference.month - dob.month - (reference.day < dob.day)
	if months >= 1:
		return f"{months}mo"

	return f"{(reference - dob).days}d"


def attach_compact_age(encounters: list) -> list:
	"""Overwrite each row's `patient_age` with the display form, in one query for the batch."""
	patients = {encounter.patient for encounter in encounters if encounter.get("patient")}
	if not patients:
		return encounters

	dob_by_patient = dict(
		frappe.get_all(
			"Patient",
			filters={"name": ["in", list(patients)]},
			fields=["name", "dob"],
			as_list=True,
		)
	)
	for encounter in encounters:
		encounter.patient_age = compact_age(dob_by_patient.get(encounter.patient))

	return encounters


def validate_bmi(doc, method):
	h = flt(doc.custom_height_m)
	w = flt(doc.custom_weight_kg)
	if h > 0 and w > 0:
		doc.custom_bmi = round(w / (h * h), 2)
	else:
		doc.custom_bmi = None
