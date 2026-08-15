import frappe
from frappe.utils import add_days, cint, today

_ACTIVE_STATUS_PRIORITY = ["In Progress", "Planned"]

UPCOMING_SESSION_LIMIT = 5

SCHEDULE_DEFAULT_DAYS = 28
SCHEDULE_MAX_DAYS = 180

ASSIGNMENT_FIELDS = ("assigned_doctor", "assigned_nurse", "assigned_driver")

TEAM_LABEL_BY_FIELD = {
	"assigned_doctor": "Doctor",
	"assigned_nurse": "Nurse",
	"assigned_driver": "Driver",
}


def find_upcoming_sessions(practitioner_field: str, practitioner: str) -> list:
	sessions = frappe.get_all(
		"Bandhu Clinic Session",
		filters={
			practitioner_field: practitioner,
			"date": [">", frappe.utils.today()],
			"status": "Planned",
		},
		fields=["name", "date", "site", "clinic", "planned_start_time", "planned_end_time"],
		order_by="date asc",
		limit=UPCOMING_SESSION_LIMIT,
	)
	return label_sites(sessions)


def label_sites(sessions: list) -> list:
	"""Swap `site` from the record id to its readable name, the way find_my_schedule does.

	Site is autonamed `SITE-.####` but the live records carry slugged ids
	(`Kalamassery-Industrial-Worksite-Site`), so the raw id is what staff were seeing.
	"""
	sites = fetch_map("Site", {session.site for session in sessions if session.site}, ["site_name"])
	for session in sessions:
		session.site = (sites.get(session.site) or frappe._dict()).site_name or session.site

	return sessions


def fetch_map(doctype: str, names: set, fields: list) -> dict:
	if not names:
		return {}
	rows = frappe.get_all(doctype, filters={"name": ["in", list(names)]}, fields=["name", *fields])
	return {row.name: row for row in rows}


def build_team(session, practitioners: dict) -> list:
	team = []
	for fieldname, label in TEAM_LABEL_BY_FIELD.items():
		practitioner = practitioners.get(session.get(fieldname))
		if not practitioner:
			continue
		team.append(
			{
				"role": label,
				"name": practitioner.practitioner_name or practitioner.name,
				"mobile": practitioner.mobile_phone,
			}
		)
	return team


def find_my_schedule(practitioner: str, days: int | None = None) -> list:
	"""Every session this practitioner is on, from today forward, with the site,
	unit, vehicle and team details already resolved."""
	horizon = min(cint(days) or SCHEDULE_DEFAULT_DAYS, SCHEDULE_MAX_DAYS)
	start = today()

	sessions = frappe.get_all(
		"Bandhu Clinic Session",
		filters={"date": ["between", [start, add_days(start, horizon)]]},
		or_filters={field: practitioner for field in ASSIGNMENT_FIELDS},
		fields=[
			"name",
			"date",
			"status",
			"site",
			"clinic",
			"unit",
			"vehicle",
			"planned_start_time",
			"planned_end_time",
			*ASSIGNMENT_FIELDS,
		],
		order_by="date asc, planned_start_time asc",
	)
	if not sessions:
		return []

	# Resolved in bulk: a per-row lookup would be five queries a session on a 4G handset.
	sites = fetch_map("Site", {s.site for s in sessions if s.site}, ["site_name", "location"])
	locations = fetch_map(
		"Bandhu Location",
		{site.location for site in sites.values() if site.location},
		["location_name", "lsg", "district", "state", "phcchc"],
	)
	units = fetch_map("Unit", {s.unit for s in sessions if s.unit}, ["unit_name", "unit_code"])
	vehicles = fetch_map("Vehicle", {s.vehicle for s in sessions if s.vehicle}, ["license_plate"])
	practitioners = fetch_map(
		"Healthcare Practitioner",
		{s.get(field) for s in sessions for field in ASSIGNMENT_FIELDS if s.get(field)},
		["practitioner_name", "mobile_phone"],
	)

	schedule = []
	for session in sessions:
		site = sites.get(session.site) or frappe._dict()
		location = locations.get(site.location) or frappe._dict()
		unit = units.get(session.unit) or frappe._dict()
		vehicle = vehicles.get(session.vehicle) or frappe._dict()

		schedule.append(
			{
				"name": session.name,
				"date": str(session.date),
				"status": session.status,
				"planned_start_time": session.planned_start_time,
				"planned_end_time": session.planned_end_time,
				"site": site.site_name or session.site,
				"clinic": session.clinic,
				"location": location.location_name,
				"lsg": location.lsg,
				"district": location.district,
				"state": location.state,
				"phcchc": location.phcchc,
				"unit": unit.unit_name or session.unit,
				"unit_code": unit.unit_code,
				"vehicle": vehicle.license_plate or session.vehicle,
				"team": build_team(session, practitioners),
			}
		)
	return schedule


def find_active_session(practitioner_field: str, practitioner: str) -> dict | None:
	today = frappe.utils.today()
	candidates = frappe.get_all(
		"Bandhu Clinic Session",
		filters={
			"date": today,
			practitioner_field: practitioner,
			"status": ["in", _ACTIVE_STATUS_PRIORITY],
		},
		fields=["name", "status", "clinic", "site", "creation"],
		order_by="creation desc",
	)
	if not candidates:
		return None

	by_status = {row.status: row for row in reversed(candidates)}
	for status in _ACTIVE_STATUS_PRIORITY:
		if status in by_status:
			return label_sites([by_status[status]])[0]
	return None
