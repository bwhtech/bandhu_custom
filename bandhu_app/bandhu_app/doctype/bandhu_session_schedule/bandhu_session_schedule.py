# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today

from bandhu_app.bandhu_app.doctype.bandhu_clinic_session.bandhu_clinic_session import (
	ASSIGNMENT_ROLE_BY_FIELD,
)

PATTERN_FIELDS = (
	"frequency",
	"monthly_mode",
	"week_of_month",
	"day_of_month",
	"valid_from",
	"valid_upto",
	"holiday_list",
)


class BandhuSessionSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from bandhu_app.bandhu_app.doctype.bandhu_session_weekday.bandhu_session_weekday import (
			BandhuSessionWeekday,
		)

		assigned_doctor: DF.Link | None
		assigned_driver: DF.Link | None
		assigned_nurse: DF.Link | None
		clinic: DF.Link
		day_of_month: DF.Int
		enabled: DF.Check
		frequency: DF.Literal["Weekly", "Fortnightly", "Monthly"]
		holiday_list: DF.Link | None
		last_generated_upto: DF.Date | None
		monthly_mode: DF.Literal["Day of Week", "Day of Month"]
		planned_end_time: DF.Time | None
		planned_start_time: DF.Time | None
		project: DF.Link | None
		site: DF.Link
		unit: DF.Link | None
		valid_from: DF.Date
		valid_upto: DF.Date | None
		vehicle: DF.Link | None
		week_of_month: DF.Literal["First", "Second", "Third", "Fourth", "Last"]
		weekdays: DF.Table[BandhuSessionWeekday]
	# end: auto-generated types

	def validate(self):
		self.derive_project_from_clinic()
		self.validate_validity_window()
		self.validate_pattern()
		self.validate_planned_times()
		self.validate_assignment_roles()
		self.clear_generated_upto_on_pattern_change()
		self.warn_about_assignment_clashes()

	def on_update(self):
		self.generate_sessions_on_save()

	def derive_project_from_clinic(self):
		# Project is read-only on the form and a fact of the Clinic, not something a caller
		# should type. Deriving it here, not in the wizard's JS alone, is what makes it
		# reliably set for the Desk form, data import and any other caller of this doctype.
		if self.clinic and not self.project:
			self.project = frappe.db.get_value("Clinic", self.clinic, "project")

	def validate_validity_window(self):
		if self.valid_upto and getdate(self.valid_upto) < getdate(self.valid_from):
			frappe.throw(_("Valid Upto cannot be earlier than Valid From."))

	def validate_pattern(self):
		uses_day_of_month = self.frequency == "Monthly" and self.monthly_mode == "Day of Month"

		if uses_day_of_month:
			if not 1 <= (self.day_of_month or 0) <= 31:
				frappe.throw(_("Day of Month must be between 1 and 31."))
			self.weekdays = []
			return

		if not self.weekdays:
			frappe.throw(_("Select at least one weekday."))

		chosen = [row.weekday for row in self.weekdays]
		if len(chosen) != len(set(chosen)):
			frappe.throw(_("The same weekday is listed more than once."))

	def validate_planned_times(self):
		if self.planned_start_time and self.planned_end_time:
			if self.planned_end_time <= self.planned_start_time:
				frappe.throw(_("Planned End Time must be after Planned Start Time."))

	def validate_assignment_roles(self):
		for fieldname, required_role in ASSIGNMENT_ROLE_BY_FIELD.items():
			practitioner = self.get(fieldname)
			if not practitioner:
				continue
			actual_role = frappe.get_cached_value("Healthcare Practitioner", practitioner, "custom_role")
			if actual_role != required_role:
				frappe.throw(
					_("{0} must be a Healthcare Practitioner with role {1}, but {2} has role {3}.").format(
						self.meta.get_field(fieldname).label,
						required_role,
						practitioner,
						actual_role or _("(none)"),
					)
				)

	def clear_generated_upto_on_pattern_change(self):
		if self.is_new() or not self.last_generated_upto:
			return

		before = self.get_doc_before_save()
		if not before:
			return

		pattern_changed = any(self.get(field) != before.get(field) for field in PATTERN_FIELDS)
		weekdays_changed = [row.weekday for row in self.weekdays] != [row.weekday for row in before.weekdays]
		if pattern_changed or weekdays_changed:
			self.last_generated_upto = None
			self.flags.pattern_changed = True

	def warn_about_assignment_clashes(self):
		from bandhu_app.bandhu_app.utils.session_schedule import (
			CLASH_CHECK_DATES,
			find_assignment_clashes,
			horizon_days,
			occurrence_dates,
		)

		dates = occurrence_dates(self, today(), add_days(today(), horizon_days()))
		clashes = find_assignment_clashes(self, dates[:CLASH_CHECK_DATES])
		if not clashes:
			return

		lines = "".join(
			"<li>{0}: {1} is already at {2} on {3}</li>".format(
				frappe.utils.escape_html(clash["role"]),
				frappe.utils.escape_html(clash["who"]),
				frappe.utils.escape_html(clash["site"] or ""),
				frappe.utils.format_date(clash["date"]),
			)
			for clash in clashes
		)
		frappe.msgprint(
			_("This schedule double-books:") + f"<ul>{lines}</ul>",
			title=_("Already Assigned Elsewhere"),
			indicator="orange",
		)

	def generate_sessions_on_save(self):
		# Saving is when the user expects the camps to exist; making them wait for the
		# nightly job means an empty list and a support call.
		from bandhu_app.bandhu_app.utils.session_schedule import (
			enqueue_session_generation,
			is_auto_generation_enabled,
		)

		if not self.enabled or not is_auto_generation_enabled():
			return

		enqueue_session_generation(self.name, regenerate=bool(self.flags.pattern_changed))
		frappe.msgprint(_("Camps are being created in the background."), alert=True)


@frappe.whitelist(methods=["POST"])
def regenerate_future_sessions(schedule: str) -> dict:
	"""Drop the schedule's future sessions that nobody has used yet and rebuild them
	from the current pattern. Sessions already under way, completed, cancelled or
	carrying patients are left exactly as they are."""
	from bandhu_app.bandhu_app.utils.session_schedule import (
		generate_sessions_for_schedule,
		remove_unused_future_sessions,
	)

	frappe.has_permission("Bandhu Session Schedule", "write", doc=schedule, throw=True)

	removed = remove_unused_future_sessions(schedule)
	created = generate_sessions_for_schedule(schedule)
	return {"removed": len(removed), "created": len(created)}
