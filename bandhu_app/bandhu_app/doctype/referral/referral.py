# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, getdate, today

CLOSED_STATUSES = ("Completed", "Lost")
FOLLOW_UP_FIELDS = ("status", "required_action_from", "referral_followup")
CALL_FIELDS = ("followup_date", "summary", "next_followup_date", "status_update")


class Referral(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from bandhu_app.bandhu_app.doctype.referral_followup.referral_followup import ReferralFollowup

		age: DF.Data | None
		clinic_session: DF.Data | None
		created_by: DF.Data | None
		created_on: DF.Datetime | None
		helpline_flag: DF.Check
		notes: DF.LongText | None
		patient: DF.Data
		patient_encounter: DF.Link | None
		priority: DF.Literal["Low", "Medium", "High"]
		project: DF.Data | None
		reason: DF.SmallText | None
		referral_by_source: DF.Data | None
		referral_followup: DF.Table[ReferralFollowup]
		referred_to: DF.Data | None
		referred_to_practitioner: DF.Link | None
		required_action_from: DF.Literal["None", "Programme", "Clinic"]
		status: DF.Literal["Pending", "In Progress", "Completed", "Lost"]
	# end: auto-generated types

	def validate(self):
		previous = self.get_doc_before_save()
		if previous and "System Manager" not in frappe.get_roles():
			if previous.status in CLOSED_STATUSES:
				frappe.throw(_("This case is already closed."))
			self.validate_only_follow_up_fields_changed(previous)
			self.validate_earlier_calls_unchanged(previous)

		self.validate_new_calls(previous)

	def validate_only_follow_up_fields_changed(self, previous):
		for field in self.meta.fields:
			if field.fieldname in FOLLOW_UP_FIELDS or field.fieldtype in ("Section Break", "Column Break"):
				continue
			if cstr(previous.get(field.fieldname)) != cstr(self.get(field.fieldname)):
				frappe.throw(_("Only the follow up can be changed on this referral."))

	def validate_earlier_calls_unchanged(self, previous):
		current_calls = {call.name: call for call in self.referral_followup}
		for earlier_call in previous.referral_followup:
			current_call = current_calls.get(earlier_call.name)
			if not current_call or any(
				cstr(earlier_call.get(fieldname)) != cstr(current_call.get(fieldname))
				for fieldname in CALL_FIELDS
			):
				frappe.throw(_("An earlier follow up cannot be changed or removed."))

	def validate_new_calls(self, previous):
		earlier_call_names = {call.name for call in previous.referral_followup} if previous else set()
		new_calls = [call for call in self.referral_followup if call.name not in earlier_call_names]
		for call in new_calls:
			if not cstr(call.summary).strip():
				frappe.throw(_("Write the follow up summary."))

		if new_calls and self.status == "In Progress":
			next_followup_date = new_calls[-1].next_followup_date
			if not next_followup_date:
				frappe.throw(_("Set the next follow up date."))
			if getdate(next_followup_date) < getdate(today()):
				frappe.throw(_("The next follow up date cannot be in the past."))
