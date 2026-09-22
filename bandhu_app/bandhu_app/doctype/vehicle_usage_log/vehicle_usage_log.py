# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class VehicleUsageLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		clinic: DF.Data | None
		clinic_session: DF.Link | None
		date: DF.Date | None
		distance: DF.Int
		driver: DF.Link | None
		end_time: DF.Time | None
		odometer_end: DF.Int
		odometer_start: DF.Int
		places_visited: DF.SmallText | None
		project: DF.Data | None
		start_time: DF.Time | None
		vehicle: DF.Link
	# end: auto-generated types

	def validate(self):
		odometer_start = cint(self.odometer_start)
		odometer_end = cint(self.odometer_end)
		if odometer_start < 0 or odometer_end < 0:
			frappe.throw(_("A km reading cannot be negative."))

		if not (odometer_start and odometer_end):
			self.distance = 0
			return

		if odometer_end < odometer_start:
			frappe.throw(_("End km cannot be less than start km."))

		self.distance = odometer_end - odometer_start
