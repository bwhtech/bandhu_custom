import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Coalesce, Count, Sum
from frappe.utils import cint, cstr, escape_html, getdate

from bandhu_app.bandhu_app.page.doctor_form.doctor_form import verify_patient_linked_to_my_session
from bandhu_app.bandhu_app.utils.clinic_stats import TEST_NOT_DONE
from bandhu_app.bandhu_app.utils.patient import compact_age
from bandhu_app.bandhu_app.utils.session import fetch_map

PATIENT_FIELDS = ["name", "patient_name", "custom_bandhu_id", "sex", "dob"]
PLACE_FILTERS = ("project", "lsg", "district")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	patient = find_patient(filters.clinic_id)
	verify_patient_linked_to_my_session(patient.name)
	rows = build_rows(fetch_visits(patient.name, filters), filters)
	return get_columns(), rows, describe_patient(patient), None, build_summary(rows)


def validate_filters(filters):
	if not cstr(filters.get("clinic_id")).strip():
		frappe.throw(_("Enter the patient's Clinic ID."))

	if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))


def find_patient(clinic_id) -> frappe._dict:
	typed = cstr(clinic_id).replace(" ", "").strip()
	matches = frappe.qb.get_query(
		"Patient",
		fields=PATIENT_FIELDS,
		filters=[["custom_bandhu_id", "=", typed], "or", ["name", "=", typed]],
		limit=2,
	).run(as_dict=True)

	if not matches:
		frappe.throw(_("No patient has Clinic ID {0}.").format(escape_html(typed)))
	return next((patient for patient in matches if patient.custom_bandhu_id == typed), matches[0])


def fetch_visits(patient: str, filters) -> list:
	visit_filters = [["patient", "=", patient], ["docstatus", "<", 2]]
	if filters.from_date:
		visit_filters.append(["encounter_date", ">=", filters.from_date])
	if filters.to_date:
		visit_filters.append(["encounter_date", "<=", filters.to_date])

	return frappe.get_all(
		"Patient Encounter",
		filters=visit_filters,
		fields=["name", "encounter_date", "custom_clinic_session", "custom_workflow_state"],
		order_by="encounter_date desc, creation desc",
	)


def build_rows(visits: list, filters) -> list:
	sessions = fetch_map(
		"Bandhu Clinic Session",
		{visit.custom_clinic_session for visit in visits if visit.custom_clinic_session},
		["project", "site"],
	)
	sites = fetch_map(
		"Site", {session.site for session in sessions.values() if session.site}, ["site_name", "location"]
	)
	locations = fetch_map(
		"Bandhu Location", {site.location for site in sites.values() if site.location}, ["lsg", "district"]
	)

	places = {}
	for visit in visits:
		session = sessions.get(visit.custom_clinic_session) or frappe._dict()
		site = sites.get(session.site) or frappe._dict()
		location = locations.get(site.location) or frappe._dict()
		place = frappe._dict(
			project=session.project,
			site=site.site_name or session.site,
			lsg=location.lsg,
			district=location.district,
		)
		if matches_filters(place, filters):
			places[visit.name] = place

	kept_visits = [visit for visit in visits if visit.name in places]
	if not kept_visits:
		return []

	encounter_names = [visit.name for visit in kept_visits]
	tests = count_tests_by_visit(encounter_names)
	medicines = count_medicines_by_visit(encounter_names)
	diagnoses = fetch_diagnoses(encounter_names)
	referrals = fetch_referrals(encounter_names)

	rows = []
	for visit in kept_visits:
		place = places[visit.name]
		test_counts = tests.get(visit.name) or frappe._dict()
		medicine_counts = medicines.get(visit.name) or frappe._dict()
		rows.append(
			{
				"date": visit.encounter_date,
				"encounter": visit.name,
				"project": place.project,
				"site": place.site,
				"lsg": place.lsg,
				"district": place.district,
				"status": visit.custom_workflow_state,
				"diagnosis": ", ".join(diagnoses.get(visit.name, [])),
				"tests_ordered": cint(test_counts.ordered),
				"tests_done": cint(test_counts.done),
				"medicines_prescribed": cint(medicine_counts.prescribed),
				"medicines_dispensed": cint(medicine_counts.dispensed),
				"referral": "; ".join(referrals.get(visit.name, [])),
			}
		)
	return rows


def matches_filters(place, filters) -> bool:
	for fieldname in PLACE_FILTERS:
		wanted = cstr(filters.get(fieldname)).strip()
		if wanted and cstr(place.get(fieldname)).casefold() != wanted.casefold():
			return False
	return True


def count_tests_by_visit(encounter_names: list) -> dict:
	test = frappe.qb.DocType("Test Instructions")
	done = Case().when(Coalesce(test.result_type, "").notin(["", TEST_NOT_DONE]), 1).else_(0)

	rows = (
		frappe.qb.from_(test)
		.select(test.parent.as_("encounter"), Count(test.name).as_("ordered"), Sum(done).as_("done"))
		.where((test.parenttype == "Patient Encounter") & (test.parent.isin(encounter_names)))
		.groupby(test.parent)
		.run(as_dict=True)
	)
	return {row.encounter: row for row in rows}


def count_medicines_by_visit(encounter_names: list) -> dict:
	prescription = frappe.qb.DocType("Prescription")
	dispensed = Case().when(prescription.dispensed == 1, 1).else_(0)

	rows = (
		frappe.qb.from_(prescription)
		.select(
			prescription.parent.as_("encounter"),
			Count(prescription.name).as_("prescribed"),
			Sum(dispensed).as_("dispensed"),
		)
		.where((prescription.parenttype == "Patient Encounter") & (prescription.parent.isin(encounter_names)))
		.groupby(prescription.parent)
		.run(as_dict=True)
	)
	return {row.encounter: row for row in rows}


def fetch_diagnoses(encounter_names: list) -> dict:
	diagnosis = frappe.qb.DocType("Bandhu Diagnosis")
	rows = (
		frappe.qb.from_(diagnosis)
		.select(diagnosis.parent, diagnosis.diagnosis_name)
		.where(
			(diagnosis.parenttype == "Patient Encounter")
			& (diagnosis.parent.isin(encounter_names))
			& (Coalesce(diagnosis.diagnosis_name, "") != "")
		)
		.orderby(diagnosis.idx)
		.run(as_dict=True)
	)

	diagnoses = {}
	for row in rows:
		diagnoses.setdefault(row.parent, []).append(row.diagnosis_name)
	return diagnoses


def fetch_referrals(encounter_names: list) -> dict:
	referrals = {}
	for referral in frappe.get_all(
		"Referral",
		filters={"patient_encounter": ["in", encounter_names]},
		fields=["patient_encounter", "referred_to", "status"],
		order_by="creation asc",
	):
		referrals.setdefault(referral.patient_encounter, []).append(
			f"{cstr(referral.referred_to) or _('Referred')} ({referral.status})"
		)
	return referrals


def describe_patient(patient) -> str:
	details = [
		patient.custom_bandhu_id or patient.name,
		patient.sex,
		compact_age(patient.dob) if patient.dob else None,
	]
	return "<b>{0}</b> | {1}".format(
		escape_html(patient.patient_name or patient.name),
		escape_html(" | ".join(cstr(detail) for detail in details if detail)),
	)


def build_summary(rows: list) -> list:
	if not rows:
		return []

	dates = [row["date"] for row in rows if row["date"]]
	return [
		{"label": _("Visits"), "value": len(rows), "datatype": "Int"},
		{"label": _("First Visit"), "value": min(dates) if dates else None, "datatype": "Date"},
		{"label": _("Last Visit"), "value": max(dates) if dates else None, "datatype": "Date"},
		{"label": _("Tests Done"), "value": sum(row["tests_done"] for row in rows), "datatype": "Int"},
		{
			"label": _("Medicines Dispensed"),
			"value": sum(row["medicines_dispensed"] for row in rows),
			"datatype": "Int",
		},
		{
			"label": _("Visits Referred"),
			"value": sum(1 for row in rows if row["referral"]),
			"datatype": "Int",
		},
	]


def get_columns() -> list:
	return [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 110},
		{
			"fieldname": "encounter",
			"label": _("Visit"),
			"fieldtype": "Link",
			"options": "Patient Encounter",
			"width": 170,
		},
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Data", "width": 130, "align": "left"},
		{"fieldname": "site", "label": _("Site"), "fieldtype": "Data", "width": 180, "align": "left"},
		{"fieldname": "lsg", "label": _("LSG"), "fieldtype": "Data", "width": 170, "align": "left"},
		{"fieldname": "district", "label": _("District"), "fieldtype": "Data", "width": 110, "align": "left"},
		{
			"fieldname": "status",
			"label": _("Visit Status"),
			"fieldtype": "Data",
			"width": 150,
			"align": "left",
		},
		{
			"fieldname": "diagnosis",
			"label": _("Diagnosis"),
			"fieldtype": "Data",
			"width": 180,
			"align": "left",
		},
		{"fieldname": "tests_ordered", "label": _("Tests Ordered"), "fieldtype": "Int", "width": 110},
		{"fieldname": "tests_done", "label": _("Tests Done"), "fieldtype": "Int", "width": 100},
		{
			"fieldname": "medicines_prescribed",
			"label": _("Medicines Prescribed"),
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"fieldname": "medicines_dispensed",
			"label": _("Medicines Dispensed"),
			"fieldtype": "Int",
			"width": 150,
		},
		{"fieldname": "referral", "label": _("Referral"), "fieldtype": "Data", "width": 220, "align": "left"},
	]
