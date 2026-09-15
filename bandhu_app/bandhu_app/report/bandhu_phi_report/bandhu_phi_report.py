import frappe
from frappe import _
from frappe.utils import cint, cstr, date_diff, getdate

from bandhu_app.bandhu_app.utils.clinic_stats import count_encounters
from bandhu_app.bandhu_app.utils.session import fetch_map

HELD_STATUSES = ["In Progress", "Completed"]
LOCATION_FILTERS = ("phcchc", "lsg", "district")
MAX_REPORT_DAYS = 366
CHART_LIMIT = 10


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	sessions = fetch_sessions(filters)
	if not sessions:
		return get_columns(), []

	rows = build_rows(sessions)
	chart = build_chart(rows)
	summary = build_summary(rows)
	return get_columns(), label_missing_locations(rows), None, chart, summary


def label_missing_locations(rows: list) -> list:
	not_set = _("Not set")
	for row in rows:
		for fieldname in LOCATION_FILTERS:
			row[fieldname] = row[fieldname] or not_set
	return rows


def validate_filters(filters):
	if not (filters.from_date and filters.to_date):
		frappe.throw(_("From Date and To Date are required."))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	if date_diff(filters.to_date, filters.from_date) > MAX_REPORT_DAYS:
		frappe.throw(_("Choose a period of {0} days or less.").format(MAX_REPORT_DAYS))


def fetch_sessions(filters) -> list:
	session_filters = {
		"date": ["between", [filters.from_date, filters.to_date]],
		"status": ["in", HELD_STATUSES],
	}

	if filters.get("project"):
		session_filters["project"] = cstr(filters.project)

	location_filters = {
		fieldname: cstr(filters.get(fieldname)).strip()
		for fieldname in LOCATION_FILTERS
		if cstr(filters.get(fieldname)).strip()
	}
	if location_filters:
		locations = frappe.get_all("Bandhu Location", filters=location_filters, pluck="name")
		if not locations:
			return []
		sites = frappe.get_all("Site", filters={"location": ["in", locations]}, pluck="name")
		if not sites:
			return []
		session_filters["site"] = ["in", sites]

	return frappe.get_all(
		"Bandhu Clinic Session",
		filters=session_filters,
		fields=["name", "date", "site"],
		order_by="date asc",
	)


def build_rows(sessions: list) -> list:
	sites = fetch_map(
		"Site", {session.site for session in sessions if session.site}, ["site_name", "location"]
	)
	locations = fetch_map(
		"Bandhu Location",
		{site.location for site in sites.values() if site.location},
		["phcchc", "lsg", "district"],
	)
	encounter_counts = count_encounters([session.name for session in sessions])

	grouped = {}
	for session in sessions:
		site = sites.get(session.site) or frappe._dict()
		location = locations.get(site.location) or frappe._dict()
		key = (session.date, location.phcchc, location.lsg, location.district)

		group = grouped.setdefault(
			key,
			{"site_names": set(), "sessions_held": 0, "patients": 0},
		)
		if site.site_name or session.site:
			group["site_names"].add(site.site_name or session.site)
		group["sessions_held"] += 1
		group["patients"] += cint((encounter_counts.get(session.name) or frappe._dict()).patients)

	rows = [
		{
			"date": date,
			"phcchc": phcchc,
			"lsg": lsg,
			"district": district,
			"sites": ", ".join(sorted(group["site_names"])),
			"sessions_held": group["sessions_held"],
			"patients": group["patients"],
		}
		for (date, phcchc, lsg, district), group in grouped.items()
	]
	return sorted(rows, key=lambda row: (row["date"], row["phcchc"] or "", row["lsg"] or ""))


def build_chart(rows: list) -> dict:
	sessions_by_phcchc = {}
	for row in rows:
		label = row["phcchc"] or _("Not set")
		sessions_by_phcchc[label] = sessions_by_phcchc.get(label, 0) + row["sessions_held"]

	busiest = sorted(sessions_by_phcchc.items(), key=lambda item: item[1], reverse=True)[:CHART_LIMIT]

	return {
		"data": {
			"labels": [label for label, count in busiest],
			"datasets": [{"name": _("Sessions Held"), "values": [count for label, count in busiest]}],
		},
		"type": "bar",
	}


def build_summary(rows: list) -> list:
	return [
		{
			"label": _("Sessions Held"),
			"value": sum(row["sessions_held"] for row in rows),
			"datatype": "Int",
		},
		{
			"label": _("PHC/CHCs Covered"),
			"value": len({row["phcchc"] for row in rows if row["phcchc"]}),
			"datatype": "Int",
		},
		{
			"label": _("LSGs Covered"),
			"value": len({row["lsg"] for row in rows if row["lsg"]}),
			"datatype": "Int",
		},
		{"label": _("Patients Seen"), "value": sum(row["patients"] for row in rows), "datatype": "Int"},
	]


def get_columns() -> list:
	return [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "phcchc", "label": _("PHC/CHC"), "fieldtype": "Data", "width": 200},
		{"fieldname": "lsg", "label": _("LSG"), "fieldtype": "Data", "width": 180},
		{"fieldname": "district", "label": _("District"), "fieldtype": "Data", "width": 110},
		{"fieldname": "sites", "label": _("Sites"), "fieldtype": "Data", "width": 260},
		{"fieldname": "sessions_held", "label": _("Sessions Held"), "fieldtype": "Int", "width": 120},
		{"fieldname": "patients", "label": _("Patients Seen"), "fieldtype": "Int", "width": 120},
	]
