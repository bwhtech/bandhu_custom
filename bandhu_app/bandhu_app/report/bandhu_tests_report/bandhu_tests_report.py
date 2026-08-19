import frappe
from frappe import _
from frappe.utils import getdate

from bandhu_app.bandhu_app.utils.patient import age_group
from bandhu_app.bandhu_app.utils.session import fetch_map

PENDING = "Pending"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	tests = fetch_tests(filters)
	if not tests:
		return get_columns(), []

	rows = build_rows(tests)
	rows = apply_result_filter(rows, filters)
	if not rows:
		return get_columns(), []

	return get_columns(), rows, None, build_chart(rows), build_summary(rows)


def validate_filters(filters):
	if not (filters.from_date and filters.to_date):
		frappe.throw(_("From Date and To Date are required."))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))


def fetch_tests(filters) -> list:
	conditions = ["session.date between %(from_date)s and %(to_date)s"]
	values = {"from_date": filters.from_date, "to_date": filters.to_date}

	for fieldname in ("project", "site", "unit", "clinic"):
		if filters.get(fieldname):
			conditions.append(f"session.{fieldname} = %({fieldname})s")
			values[fieldname] = filters.get(fieldname)

	if filters.get("location"):
		conditions.append("site.location = %(location)s")
		values["location"] = filters.location

	if filters.get("test_name"):
		conditions.append("test.test_name = %(test_name)s")
		values["test_name"] = filters.test_name

	return frappe.db.sql(
		f"""
		select
			session.date,
			session.name as camp,
			session.site as site_id,
			session.project,
			session.unit as unit_id,
			session.assigned_doctor as doctor_id,
			encounter.name as encounter,
			encounter.patient,
			test.test_name,
			test.result_type,
			test.result_value
		from `tabTest Instructions` test
		inner join `tabPatient Encounter` encounter on encounter.name = test.parent
		inner join `tabBandhu Clinic Session` session on session.name = encounter.custom_clinic_session
		left join `tabSite` site on site.name = session.site
		where test.parenttype = 'Patient Encounter'
			and encounter.docstatus < 2
			and {" and ".join(conditions)}
		order by session.date asc, encounter.name asc, test.idx asc
		""",
		values,
		as_dict=True,
	)


def build_rows(tests: list) -> list:
	sites = fetch_map(
		"Site", {test.site_id for test in tests if test.site_id}, ["site_name", "location"]
	)
	locations = fetch_map(
		"Bandhu Location",
		{site.location for site in sites.values() if site.location},
		["lsg", "district"],
	)
	units = fetch_map("Unit", {test.unit_id for test in tests if test.unit_id}, ["unit_name"])
	doctors = fetch_map(
		"Healthcare Practitioner",
		{test.doctor_id for test in tests if test.doctor_id},
		["practitioner_name"],
	)
	patients = fetch_map(
		"Patient",
		{test.patient for test in tests if test.patient},
		["patient_name", "sex", "dob", "custom_bandhu_id", "custom_native_state"],
	)

	rows = []
	for test in tests:
		site = sites.get(test.site_id) or frappe._dict()
		location = locations.get(site.location) or frappe._dict()
		patient = patients.get(test.patient) or frappe._dict()

		rows.append(
			{
				"date": test.date,
				"camp": test.camp,
				"site": site.site_name or test.site_id,
				"lsg": location.lsg,
				"district": location.district,
				"project": test.project,
				"unit": (units.get(test.unit_id) or frappe._dict()).unit_name or test.unit_id,
				"doctor": (doctors.get(test.doctor_id) or frappe._dict()).practitioner_name
				or test.doctor_id,
				"clinic_id": patient.custom_bandhu_id,
				"patient": test.patient,
				"patient_name": patient.patient_name,
				"sex": patient.sex,
				"age_group": age_group(patient.dob, test.date),
				"native_state": patient.custom_native_state,
				"test_name": test.test_name,
				"result": test.result_type or PENDING,
				"result_value": test.result_value,
				"encounter": test.encounter,
			}
		)
	return rows


def apply_result_filter(rows: list, filters) -> list:
	"""Pending is the absence of a result, so it cannot be a SQL equality like the rest."""
	if not filters.get("result"):
		return rows

	return [row for row in rows if row["result"] == filters.result]


def build_chart(rows: list) -> dict:
	test_names = sorted({row["test_name"] for row in rows if row["test_name"]})
	done = [
		len([row for row in rows if row["test_name"] == name and row["result"] != PENDING])
		for name in test_names
	]
	positive = [
		len([row for row in rows if row["test_name"] == name and row["result"] == "Positive"])
		for name in test_names
	]

	return {
		"data": {
			"labels": test_names,
			"datasets": [
				{"name": _("Done"), "values": done},
				{"name": _("Positive"), "values": positive},
			],
		},
		"type": "bar",
	}


def build_summary(rows: list) -> list:
	done = [row for row in rows if row["result"] != PENDING]

	return [
		{"label": _("Tests Ordered"), "value": len(rows), "datatype": "Int"},
		{"label": _("Tests Done"), "value": len(done), "datatype": "Int"},
		{
			"label": _("Positive"),
			"value": len([row for row in done if row["result"] == "Positive"]),
			"datatype": "Int",
		},
		{
			"label": _("Awaiting Result"),
			"value": len(rows) - len(done),
			"datatype": "Int",
		},
		{
			"label": _("Patients Tested"),
			"value": len({row["patient"] for row in rows}),
			"datatype": "Int",
		},
	]


def get_columns() -> list:
	return [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "test_name", "label": _("Test"), "fieldtype": "Data", "width": 120},
		{"fieldname": "result", "label": _("Result"), "fieldtype": "Data", "width": 100},
		{"fieldname": "result_value", "label": _("Value"), "fieldtype": "Data", "width": 110},
		{"fieldname": "clinic_id", "label": _("Clinic ID"), "fieldtype": "Data", "width": 120},
		{"fieldname": "patient_name", "label": _("Patient"), "fieldtype": "Data", "width": 160},
		{"fieldname": "sex", "label": _("Sex"), "fieldtype": "Data", "width": 80},
		{"fieldname": "age_group", "label": _("Age Group"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "native_state",
			"label": _("Native State"),
			"fieldtype": "Data",
			"width": 130,
		},
		{"fieldname": "site", "label": _("Site"), "fieldtype": "Data", "width": 180},
		{"fieldname": "lsg", "label": _("LSG"), "fieldtype": "Data", "width": 130},
		{"fieldname": "district", "label": _("District"), "fieldtype": "Data", "width": 110},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Bandhu Projects",
			"width": 130,
		},
		{"fieldname": "unit", "label": _("Unit"), "fieldtype": "Data", "width": 110},
		{"fieldname": "doctor", "label": _("Doctor"), "fieldtype": "Data", "width": 140},
		{
			"fieldname": "camp",
			"label": _("Camp"),
			"fieldtype": "Link",
			"options": "Bandhu Clinic Session",
			"width": 150,
		},
		{
			"fieldname": "encounter",
			"label": _("Encounter"),
			"fieldtype": "Link",
			"options": "Patient Encounter",
			"width": 150,
		},
	]
