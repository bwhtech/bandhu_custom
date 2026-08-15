# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

import json
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import getdate, today

WEEKDAY_INDEX = {
	"Monday": 0,
	"Tuesday": 1,
	"Wednesday": 2,
	"Thursday": 3,
	"Friday": 4,
	"Saturday": 5,
	"Sunday": 6,
}

WEEK_OF_MONTH_OFFSET = {"First": 0, "Second": 1, "Third": 2, "Fourth": 3}

DEFAULT_HORIZON_DAYS = 56
PREVIEW_LIMIT = 10

SESSION_FIELDS_FROM_SCHEDULE = (
	"site",
	"clinic",
	"project",
	"unit",
	"planned_start_time",
	"planned_end_time",
	"assigned_doctor",
	"assigned_nurse",
	"assigned_driver",
	"vehicle",
)


def week_start(day: date) -> date:
	return day - timedelta(days=day.weekday())


def first_day_of_next_month(day: date) -> date:
	if day.month == 12:
		return date(day.year + 1, 1, 1)
	return date(day.year, day.month + 1, 1)


def last_day_of_month(day: date) -> date:
	return first_day_of_next_month(day) - timedelta(days=1)


def selected_weekday_indexes(schedule) -> set:
	return {WEEKDAY_INDEX[row.weekday] for row in schedule.weekdays if row.weekday}


def holiday_dates(holiday_list: str | None) -> set:
	if not holiday_list:
		return set()
	return set(frappe.get_all("Holiday", filters={"parent": holiday_list}, pluck="holiday_date"))


def nth_weekday_of_month(year: int, month: int, weekday: int, week_of_month: str) -> date | None:
	first = date(year, month, 1)
	first_match = first + timedelta(days=(weekday - first.weekday()) % 7)

	if week_of_month == "Last":
		last = last_day_of_month(first)
		occurrence = first_match
		while occurrence + timedelta(days=7) <= last:
			occurrence += timedelta(days=7)
		return occurrence

	occurrence = first_match + timedelta(days=7 * WEEK_OF_MONTH_OFFSET.get(week_of_month, 0))
	# A fifth Tuesday does not exist in every month; the month is skipped, not shifted.
	return occurrence if occurrence.month == month else None


def weekly_dates(schedule, start: date, end: date) -> list:
	weekdays = selected_weekday_indexes(schedule)
	if not weekdays:
		return []

	anchor_week = week_start(getdate(schedule.valid_from))
	dates = []
	current = start
	while current <= end:
		if current.weekday() in weekdays:
			is_on_week = (week_start(current) - anchor_week).days // 7 % 2 == 0
			if schedule.frequency != "Fortnightly" or is_on_week:
				dates.append(current)
		current += timedelta(days=1)
	return dates


def monthly_weekday_dates(schedule, start: date, end: date) -> list:
	weekdays = selected_weekday_indexes(schedule)
	if not weekdays:
		return []

	dates = []
	month = date(start.year, start.month, 1)
	while month <= end:
		for weekday in weekdays:
			occurrence = nth_weekday_of_month(
				month.year, month.month, weekday, schedule.week_of_month or "First"
			)
			if occurrence and start <= occurrence <= end:
				dates.append(occurrence)
		month = first_day_of_next_month(month)
	return sorted(dates)


def monthly_day_of_month_dates(schedule, start: date, end: date) -> list:
	day_of_month = int(schedule.day_of_month or 0)
	if not 1 <= day_of_month <= 31:
		return []

	dates = []
	month = date(start.year, start.month, 1)
	while month <= end:
		if day_of_month <= last_day_of_month(month).day:
			occurrence = date(month.year, month.month, day_of_month)
			if start <= occurrence <= end:
				dates.append(occurrence)
		month = first_day_of_next_month(month)
	return dates


def occurrence_dates(schedule, from_date, to_date) -> list:
	start = max(getdate(from_date), getdate(schedule.valid_from))
	end = getdate(to_date)
	if schedule.valid_upto:
		end = min(end, getdate(schedule.valid_upto))
	if start > end:
		return []

	if schedule.frequency == "Monthly" and schedule.monthly_mode == "Day of Month":
		dates = monthly_day_of_month_dates(schedule, start, end)
	elif schedule.frequency == "Monthly":
		dates = monthly_weekday_dates(schedule, start, end)
	else:
		dates = weekly_dates(schedule, start, end)

	holidays = holiday_dates(schedule.holiday_list)
	return [day for day in dates if day not in holidays]


def horizon_days() -> int:
	configured = frappe.db.get_single_value("Bandhu Settings", "session_horizon_days")
	return int(configured or DEFAULT_HORIZON_DAYS)


def is_auto_generation_enabled() -> bool:
	# Phrased as an opt-out because a Single stores nothing until it is first saved,
	# and an unread Check comes back as 0 — indistinguishable from "switched off".
	return not frappe.db.get_single_value("Bandhu Settings", "disable_auto_session_generation")


def build_session(schedule, day: date):
	session = frappe.new_doc("Bandhu Clinic Session")
	session.session_schedule = schedule.name
	session.date = day
	session.status = "Planned"
	for fieldname in SESSION_FIELDS_FROM_SCHEDULE:
		session.set(fieldname, schedule.get(fieldname))
	return session


def generate_sessions_for_schedule(schedule, upto=None) -> list:
	"""Create the schedule's missing sessions from today up to the horizon."""
	if isinstance(schedule, str):
		schedule = frappe.get_doc("Bandhu Session Schedule", schedule)

	start = getdate(today())
	end = getdate(upto) if upto else start + timedelta(days=horizon_days())
	dates = occurrence_dates(schedule, start, end)
	if not dates:
		schedule.db_set("last_generated_upto", end, update_modified=False)
		return []

	# A date already carrying a session is never regenerated, whatever its status —
	# that is what stops a session cancelled for a holiday from reappearing tonight.
	already_generated = set(
		frappe.get_all(
			"Bandhu Clinic Session",
			filters={"session_schedule": schedule.name, "date": ["in", dates]},
			pluck="date",
		)
	)

	created = []
	for day in dates:
		if day in already_generated:
			continue
		session = build_session(schedule, day)
		session.insert()
		created.append(session.name)

	schedule.db_set("last_generated_upto", end, update_modified=False)
	return created


def generate_scheduled_sessions():
	"""Nightly entry point. Registered in hooks.py under scheduler_events."""
	if not is_auto_generation_enabled():
		return

	schedules = frappe.get_all("Bandhu Session Schedule", filters={"enabled": 1}, pluck="name")
	for index, name in enumerate(schedules):
		savepoint = f"session_schedule_{index}"
		frappe.db.savepoint(savepoint)
		try:
			generate_sessions_for_schedule(name)
		except Exception:
			# One malformed schedule must not cost every other schedule its sessions.
			frappe.db.rollback(save_point=savepoint)
			frappe.log_error(title=f"Session generation failed for {name}")


ASSIGNMENT_LABELS = {
	"assigned_doctor": "Doctor",
	"assigned_nurse": "Nurse",
	"assigned_driver": "Driver",
	"vehicle": "Vehicle",
}

CLASH_CHECK_DATES = 10


def find_assignment_clashes(schedule, dates: list) -> list:
	"""Staff or a vehicle already committed to another camp on one of these dates.
	Reported, never blocked — a genuine double-booking is sometimes intentional."""
	if not dates:
		return []

	assigned = {field: schedule.get(field) for field in ASSIGNMENT_LABELS if schedule.get(field)}
	if not assigned:
		return []

	sessions = frappe.get_all(
		"Bandhu Clinic Session",
		filters={"date": ["in", dates], "status": ["!=", "Cancelled"]},
		or_filters=assigned,
		fields=["name", "date", "site", "session_schedule", *ASSIGNMENT_LABELS],
	)

	practitioner_names = dict(
		frappe.get_all(
			"Healthcare Practitioner",
			filters={"name": ["in", list(assigned.values())]},
			fields=["name", "practitioner_name"],
			as_list=True,
		)
	)

	clashes = []
	for session in sessions:
		if schedule.get("name") and session.session_schedule == schedule.get("name"):
			continue
		for field, value in assigned.items():
			if session.get(field) != value:
				continue
			clashes.append(
				{
					"date": str(session.date),
					"role": ASSIGNMENT_LABELS[field],
					"who": practitioner_names.get(value, value),
					"site": session.site,
					"session": session.name,
				}
			)
	return clashes


@frappe.whitelist()
def preview_occurrences(schedule: str) -> list:
	"""Next few dates for a schedule the user is still editing, so the pattern is
	visible before it creates anything."""
	frappe.has_permission("Bandhu Session Schedule", "read", throw=True)

	values = json.loads(schedule) if isinstance(schedule, str) else schedule
	values["doctype"] = "Bandhu Session Schedule"
	draft = frappe.get_doc(values)
	if not draft.valid_from:
		frappe.throw(_("Set Valid From before previewing dates."))

	start = getdate(today())
	end = start + timedelta(days=horizon_days())
	return [str(day) for day in occurrence_dates(draft, start, end)[:PREVIEW_LIMIT]]


@frappe.whitelist()
def generate_now(schedule: str) -> list:
	frappe.has_permission("Bandhu Session Schedule", "write", doc=schedule, throw=True)
	return generate_sessions_for_schedule(schedule)
