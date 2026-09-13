import frappe
from frappe import _
from frappe.utils import add_days, cstr, date_diff, getdate

from bandhu_app.bandhu_app.utils.session import fetch_map

MAX_REPORT_DAYS = 366
CHART_LIMIT = 10
STATUS_FIELDS = {
	"Pending": "pending",
	"In Progress": "in_progress",
	"Completed": "completed",
	"Lost": "lost",
}
OPEN_STATUSES = ("Pending", "In Progress")
PLACE_TEXT_FILTERS = ("lsg", "district")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	referrals = [referral for referral in fetch_referrals(filters) if matches_filters(referral, filters)]
	if not referrals:
		return get_columns(), []

	return get_columns(), build_rows(referrals), None, build_chart(referrals), build_summary(referrals)


def validate_filters(filters):
	if not (filters.from_date and filters.to_date):
		frappe.throw(_("From Date and To Date are required."))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	if date_diff(filters.to_date, filters.from_date) > MAX_REPORT_DAYS:
		frappe.throw(_("Choose a period of {0} days or less.").format(MAX_REPORT_DAYS))


def fetch_referrals(filters) -> list:
	referral_filters = [
		["creation", ">=", getdate(filters.from_date)],
		["creation", "<", add_days(getdate(filters.to_date), 1)],
	]
	for fieldname in ("project", "status"):
		if cstr(filters.get(fieldname)).strip():
			referral_filters.append([fieldname, "=", cstr(filters.get(fieldname)).strip()])

	referrals = frappe.get_all(
		"Referral",
		filters=referral_filters,
		fields=["name", "patient", "patient_encounter", "clinic_session", "referred_to", "status"],
		order_by="creation asc",
	)
	return attach_places(referrals)


def attach_places(referrals: list) -> list:
	encounters = fetch_map(
		"Patient Encounter",
		{referral.patient_encounter for referral in referrals if referral.patient_encounter},
		["custom_clinic_session"],
	)
	session_by_referral = {
		referral.name: referral.clinic_session
		or (encounters.get(referral.patient_encounter) or frappe._dict()).custom_clinic_session
		for referral in referrals
	}
	sessions = fetch_map(
		"Bandhu Clinic Session",
		{session for session in session_by_referral.values() if session},
		["unit", "site"],
	)
	sites = fetch_map("Site", {session.site for session in sessions.values() if session.site}, ["location"])
	locations = fetch_map(
		"Bandhu Location", {site.location for site in sites.values() if site.location}, ["lsg", "district"]
	)
	units = fetch_map("Unit", {session.unit for session in sessions.values() if session.unit}, ["unit_name"])

	placed = []
	for referral in referrals:
		session = sessions.get(session_by_referral[referral.name]) or frappe._dict()
		location = locations.get((sites.get(session.site) or frappe._dict()).location) or frappe._dict()
		placed.append(
			frappe._dict(
				patient=referral.patient,
				referred_to=referral.referred_to,
				status=referral.status,
				unit_id=session.unit,
				unit=(units.get(session.unit) or frappe._dict()).unit_name
				or session.unit
				or _("Not recorded"),
				lsg=location.lsg,
				district=location.district,
			)
		)
	return placed


def matches_filters(referral, filters) -> bool:
	if filters.get("unit") and referral.unit_id != cstr(filters.unit):
		return False

	for fieldname in PLACE_TEXT_FILTERS:
		wanted = cstr(filters.get(fieldname)).strip()
		if wanted and cstr(referral.get(fieldname)).casefold() != wanted.casefold():
			return False
	return True


def build_rows(referrals: list) -> list:
	groups = {}
	for referral in referrals:
		key = (referral.unit, referral.lsg, referral.district)
		group = groups.setdefault(
			key,
			{"patients": set(), "referrals": 0, **dict.fromkeys(STATUS_FIELDS.values(), 0)},
		)
		group["patients"].add(referral.patient)
		group["referrals"] += 1
		if referral.status in STATUS_FIELDS:
			group[STATUS_FIELDS[referral.status]] += 1

	rows = [
		{
			"unit": unit,
			"lsg": lsg,
			"district": district,
			"people_referred": len(group["patients"]),
			"referrals": group["referrals"],
			**{fieldname: group[fieldname] for fieldname in STATUS_FIELDS.values()},
		}
		for (unit, lsg, district), group in groups.items()
	]
	return sorted(rows, key=lambda row: row["referrals"], reverse=True)


def build_chart(referrals: list) -> dict:
	counts = {}
	for referral in referrals:
		label = referral.referred_to or _("Not recorded")
		counts[label] = counts.get(label, 0) + 1

	busiest = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:CHART_LIMIT]

	return {
		"data": {
			"labels": [label for label, count in busiest],
			"datasets": [{"name": _("Referrals"), "values": [count for label, count in busiest]}],
		},
		"type": "bar",
	}


def build_summary(referrals: list) -> list:
	return [
		{
			"label": _("People Referred"),
			"value": len({referral.patient for referral in referrals}),
			"datatype": "Int",
		},
		{"label": _("Referrals"), "value": len(referrals), "datatype": "Int"},
		{
			"label": _("Completed"),
			"value": sum(1 for referral in referrals if referral.status == "Completed"),
			"datatype": "Int",
		},
		{
			"label": _("Still Open"),
			"value": sum(1 for referral in referrals if referral.status in OPEN_STATUSES),
			"datatype": "Int",
		},
	]


def get_columns() -> list:
	return [
		{"fieldname": "unit", "label": _("Unit"), "fieldtype": "Data", "width": 160, "align": "left"},
		{"fieldname": "lsg", "label": _("LSG"), "fieldtype": "Data", "width": 190, "align": "left"},
		{"fieldname": "district", "label": _("District"), "fieldtype": "Data", "width": 120, "align": "left"},
		{"fieldname": "people_referred", "label": _("People Referred"), "fieldtype": "Int", "width": 130},
		{"fieldname": "referrals", "label": _("Referrals"), "fieldtype": "Int", "width": 100},
		{"fieldname": "pending", "label": _("Pending"), "fieldtype": "Int", "width": 90},
		{"fieldname": "in_progress", "label": _("In Progress"), "fieldtype": "Int", "width": 100},
		{"fieldname": "completed", "label": _("Completed"), "fieldtype": "Int", "width": 100},
		{"fieldname": "lost", "label": _("Lost"), "fieldtype": "Int", "width": 80},
	]
