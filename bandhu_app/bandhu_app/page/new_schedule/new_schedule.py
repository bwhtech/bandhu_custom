from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

from bandhu_app.bandhu_app.utils.session_schedule import (
	ACCEPTED_FIELDS,
	PREVIEW_LIMIT,
	WEEKDAYS,
	as_draft,
	find_assignment_clashes,
	horizon_days,
	occurrence_dates,
)

FREQUENCY_CHOICES = [
	{"value": "Weekly", "label": "Every week"},
	{"value": "Fortnightly", "label": "Every two weeks"},
	{"value": "Monthly", "label": "Once a month"},
]


PRACTITIONER_FIELD_BY_ROLE = {
	"assigned_doctor": "Doctor",
	"assigned_nurse": "Nurse",
	"assigned_driver": "Clinic Assistant cum Driver",
}


def require_scheduling_access() -> None:
	if "System Manager" not in frappe.get_roles():
		frappe.throw(
			_("You do not have permission to create clinic schedules."),
			frappe.PermissionError,
		)


def practitioners_by_role(custom_role: str) -> list:
	return frappe.get_all(
		"Healthcare Practitioner",
		filters={"custom_role": custom_role, "status": "Active"},
		fields=["name as value", "practitioner_name as label"],
		order_by="practitioner_name asc",
	)


@frappe.whitelist()
def get_form_options() -> dict:
	require_scheduling_access()

	sites = frappe.get_all("Site", fields=["name as value", "site_name as label"], order_by="site_name asc")
	clinics = frappe.get_all("Clinic", fields=["name as value", "clinic_name as label", "project", "vehicle"])

	return {
		"sites": sites,
		"clinics": clinics,
		"projects": frappe.get_all("Bandhu Projects", pluck="name"),
		"units": frappe.get_all("Unit", fields=["name as value", "unit_name as label"]),
		"vehicles": frappe.get_all("Vehicle", pluck="name"),
		"holiday_lists": frappe.get_all("Holiday List", pluck="name"),
		"doctors": practitioners_by_role("Doctor"),
		"nurses": practitioners_by_role("Nurse"),
		"drivers": practitioners_by_role("Clinic Assistant cum Driver"),
		"frequencies": FREQUENCY_CHOICES,
		"weekdays": WEEKDAYS,
		"defaults": last_used_defaults(),
		"associations": association_maps(),
	}


def association_maps() -> dict:
	"""Project/Site/Clinic/Unit pairings actually run before, so the wizard's dropdowns can
	narrow to what makes sense instead of every master in the system. Only Clinic.project is
	a real schema link — Site and Unit have no FK to Project or Clinic — so this is derived
	from history, not the doctypes, and an empty map for a key means "no history yet",
	which callers must treat as "don't filter" rather than "nothing is valid"."""
	combos = frappe.get_all("Bandhu Clinic Session", fields=["project", "site", "clinic", "unit"])

	project_sites = defaultdict(set)
	site_clinics = defaultdict(set)
	clinic_units = defaultdict(set)
	for combo in combos:
		if combo.project and combo.site:
			project_sites[combo.project].add(combo.site)
		if combo.site and combo.clinic:
			site_clinics[combo.site].add(combo.clinic)
		if combo.clinic and combo.unit:
			clinic_units[combo.clinic].add(combo.unit)

	return {
		"project_sites": {key: sorted(value) for key, value in project_sites.items()},
		"site_clinics": {key: sorted(value) for key, value in site_clinics.items()},
		"clinic_units": {key: sorted(value) for key, value in clinic_units.items()},
	}


def clock_value(value, fallback: str) -> str:
	"""`<input type="time">` silently renders empty unless the value is zero-padded, and
	Frappe hands a Time back as `9:30:00`."""
	if value in (None, ""):
		return fallback
	hours, minutes, seconds = (str(value).split(":") + ["00", "00"])[:3]
	return f"{int(hours):02d}:{minutes:0>2}:{seconds[:2]:0>2}"


def last_used_defaults() -> dict:
	"""Prefill from the most recent schedule — the second schedule of a round is nearly
	always the same times as the first."""
	recent = frappe.get_all(
		"Bandhu Session Schedule",
		fields=["planned_start_time", "planned_end_time", "project", "holiday_list"],
		order_by="creation desc",
		limit=1,
	)
	defaults = recent[0] if recent else {}
	return {
		"planned_start_time": clock_value(defaults.get("planned_start_time"), "09:30:00"),
		"planned_end_time": clock_value(defaults.get("planned_end_time"), "13:30:00"),
		"project": defaults.get("project"),
		"holiday_list": defaults.get("holiday_list"),
		"valid_from": today(),
	}


@frappe.whitelist()
def preview_schedule(values: str) -> dict:
	require_scheduling_access()

	draft = as_draft(values)
	if not draft.valid_from:
		draft.valid_from = today()

	dates = occurrence_dates(draft, today(), add_days(today(), horizon_days()))
	four_weeks_out = getdate(add_days(today(), 28))

	return {
		"dates": [str(day) for day in dates[:PREVIEW_LIMIT]],
		"total": len(dates),
		"clashes": find_assignment_clashes(draft, dates[:PREVIEW_LIMIT]),
		"next_4_weeks": [str(day) for day in dates if day <= four_weeks_out],
	}


@frappe.whitelist(methods=["POST"])
def create_schedule(values: str) -> dict:
	require_scheduling_access()

	draft = as_draft(values)
	draft.enabled = 1
	draft.insert()

	# The camps themselves are built by a background job, so counting rows here would report
	# zero. The pattern is what the wizard can promise: a new schedule owns none of its dates
	# yet, so every occurrence in the horizon becomes a camp.
	scheduled = occurrence_dates(draft, today(), add_days(today(), horizon_days()))
	return {"name": draft.name, "scheduled": len(scheduled)}
