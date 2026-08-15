import frappe
from frappe import _
from frappe.utils import add_days, today

from bandhu_app.bandhu_app.utils.session_schedule import (
	PREVIEW_LIMIT,
	find_assignment_clashes,
	horizon_days,
	occurrence_dates,
)

FREQUENCY_CHOICES = [
	{"value": "Weekly", "label": "Every week"},
	{"value": "Fortnightly", "label": "Every two weeks"},
	{"value": "Monthly", "label": "Once a month"},
]

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

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


ACCEPTED_FIELDS = (
	"site",
	"clinic",
	"project",
	"unit",
	"vehicle",
	"frequency",
	"monthly_mode",
	"week_of_month",
	"day_of_month",
	"planned_start_time",
	"planned_end_time",
	"valid_from",
	"valid_upto",
	"holiday_list",
	"assigned_doctor",
	"assigned_nurse",
	"assigned_driver",
)


def as_draft(values) -> "frappe.model.document.Document":
	"""Turn the wizard's payload into an unsaved schedule so the same date maths and
	clash check serve the preview and the real save."""
	values = frappe.parse_json(values) or {}
	weekdays = values.get("weekdays") or []

	draft = frappe.new_doc("Bandhu Session Schedule")
	# Only the wizard's own fields are copied: passing the whole payload to update() let a
	# caller set name, owner or last_generated_upto.
	draft.update(
		{
			field: values[field]
			for field in ACCEPTED_FIELDS
			if values.get(field) not in (None, "")
		}
	)
	for weekday in weekdays:
		if weekday in WEEKDAYS:
			draft.append("weekdays", {"weekday": weekday})
	return draft


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
	return {
		"dates": [str(day) for day in dates[:PREVIEW_LIMIT]],
		"total": len(dates),
		"clashes": find_assignment_clashes(draft, dates[:PREVIEW_LIMIT]),
	}


@frappe.whitelist()
def create_schedule(values: str) -> dict:
	require_scheduling_access()

	draft = as_draft(values)
	draft.enabled = 1
	draft.insert()

	created = frappe.db.count("Bandhu Clinic Session", {"session_schedule": draft.name})
	return {"name": draft.name, "created": created}
