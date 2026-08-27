import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from bandhu_app.bandhu_app.utils.clinic_stats import (
	count_encounters,
	count_medicines,
	count_new_patients,
	count_tests,
)
from bandhu_app.bandhu_app.utils.session import fetch_map

GROUP_BY_FIELD = {"Clinic": "clinic", "Project": "project", "Unit": "unit", "LSG": "lsg", "Site": "site"}
HELD_STATUSES = ("In Progress", "Completed")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	sessions = fetch_sessions(filters)
	if not sessions:
		return get_columns(filters), []

	rows = build_rows(sessions, filters.get("group_by") or "Clinic")
	return get_columns(filters), rows, None, build_chart(rows), build_summary(rows)


def validate_filters(filters):
	if not (filters.from_date and filters.to_date):
		frappe.throw(_("From Date and To Date are required."))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	group_by = filters.get("group_by")
	if group_by and group_by not in GROUP_BY_FIELD:
		frappe.throw(_("Unknown grouping: {0}").format(group_by))


def fetch_sessions(filters) -> list:
	session_filters = {"date": ["between", [filters.from_date, filters.to_date]]}

	for fieldname in ("project", "site", "unit", "clinic"):
		if filters.get(fieldname):
			session_filters[fieldname] = filters.get(fieldname)

	if filters.get("location"):
		sites = frappe.get_all("Site", filters={"location": filters.location}, pluck="name")
		if not sites:
			return []
		if session_filters.get("site") and session_filters["site"] not in sites:
			return []
		session_filters["site"] = session_filters.get("site") or ["in", sites]

	return frappe.get_all(
		"Bandhu Clinic Session",
		filters=session_filters,
		fields=["name", "date", "status", "project", "site", "unit", "clinic"],
	)


def build_rows(sessions: list, group_by: str) -> list:
	session_names = [session.name for session in sessions]

	sites = fetch_map(
		"Site", {session.site for session in sessions if session.site}, ["site_name", "location"]
	)
	locations = fetch_map(
		"Bandhu Location", {site.location for site in sites.values() if site.location}, ["lsg"]
	)
	units = fetch_map("Unit", {session.unit for session in sessions if session.unit}, ["unit_name"])

	encounter_counts = count_encounters(session_names)
	new_patient_counts = count_new_patients(session_names)
	test_counts = count_tests(session_names)
	medicine_counts = count_medicines(session_names)

	totals = {}
	for session in sessions:
		key = group_key(session, group_by, sites, locations, units)
		row = totals.setdefault(
			key,
			{
				"group": key,
				"camps_planned": 0,
				"camps_held": 0,
				"camps_cancelled": 0,
				"patients": 0,
				"new_patients": 0,
				"repeat_patients": 0,
				"completed": 0,
				"tests_done": 0,
				"medicines_dispensed": 0,
			},
		)

		counts = encounter_counts.get(session.name) or frappe._dict()
		tests = test_counts.get(session.name) or frappe._dict()
		medicines = medicine_counts.get(session.name) or frappe._dict()
		patients = cint(counts.patients)
		new_patients = new_patient_counts.get(session.name, 0)

		row["camps_planned"] += 1
		row["camps_held"] += 1 if session.status in HELD_STATUSES else 0
		row["camps_cancelled"] += 1 if session.status == "Cancelled" else 0
		row["patients"] += patients
		row["new_patients"] += new_patients
		row["repeat_patients"] += patients - new_patients
		row["completed"] += cint(counts.completed)
		row["tests_done"] += cint(tests.done)
		row["medicines_dispensed"] += cint(medicines.dispensed)

	rows = sorted(totals.values(), key=lambda row: row["patients"], reverse=True)
	for row in rows:
		row["patients_per_camp"] = flt(row["patients"] / row["camps_held"], 1) if row["camps_held"] else 0

	return rows


def group_key(session, group_by: str, sites: dict, locations: dict, units: dict) -> str:
	if group_by == "LSG":
		site = sites.get(session.site) or frappe._dict()
		return (locations.get(site.location) or frappe._dict()).lsg or _("Unknown")

	if group_by == "Site":
		return (sites.get(session.site) or frappe._dict()).site_name or session.site or _("Unknown")

	if group_by == "Unit":
		return (units.get(session.unit) or frappe._dict()).unit_name or session.unit or _("Unknown")

	return session.get(GROUP_BY_FIELD[group_by]) or _("Unknown")


def build_chart(rows: list) -> dict:
	return {
		"data": {
			"labels": [row["group"] for row in rows],
			"datasets": [{"name": _("Patients Seen"), "values": [row["patients"] for row in rows]}],
		},
		"type": "bar",
	}


def build_summary(rows: list) -> list:
	camps_held = sum(row["camps_held"] for row in rows)
	patients = sum(row["patients"] for row in rows)

	return [
		{"label": _("Camps Held"), "value": camps_held, "datatype": "Int"},
		{
			"label": _("Camps Cancelled"),
			"value": sum(row["camps_cancelled"] for row in rows),
			"datatype": "Int",
		},
		{"label": _("Patients Seen"), "value": patients, "datatype": "Int"},
		{
			"label": _("Avg Patients per Camp"),
			"value": flt(patients / camps_held, 1) if camps_held else 0,
			"datatype": "Float",
		},
	]


def get_columns(filters) -> list:
	return [
		{
			"fieldname": "group",
			"label": _(filters.get("group_by") or "Clinic"),
			"fieldtype": "Data",
			"width": 220,
		},
		{"fieldname": "camps_planned", "label": _("Camps Scheduled"), "fieldtype": "Int", "width": 140},
		{"fieldname": "camps_held", "label": _("Camps Held"), "fieldtype": "Int", "width": 110},
		{"fieldname": "camps_cancelled", "label": _("Cancelled"), "fieldtype": "Int", "width": 100},
		{"fieldname": "patients", "label": _("Patients"), "fieldtype": "Int", "width": 100},
		{"fieldname": "new_patients", "label": _("New"), "fieldtype": "Int", "width": 80},
		{"fieldname": "repeat_patients", "label": _("Repeat"), "fieldtype": "Int", "width": 90},
		{
			"fieldname": "patients_per_camp",
			"label": _("Per Camp"),
			"fieldtype": "Float",
			"width": 100,
			# Summing an average across rows produces a number that means nothing.
			"disable_total": True,
		},
		{"fieldname": "completed", "label": _("Completed"), "fieldtype": "Int", "width": 110},
		{"fieldname": "tests_done", "label": _("Tests Done"), "fieldtype": "Int", "width": 110},
		{
			"fieldname": "medicines_dispensed",
			"label": _("Medicines Dispensed"),
			"fieldtype": "Int",
			"width": 160,
		},
	]
