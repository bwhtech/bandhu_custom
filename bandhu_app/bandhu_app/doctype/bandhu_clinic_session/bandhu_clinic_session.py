# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BandhuClinicSession(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		arrival_time: DF.Time | None
		assigned_doctor: DF.Link | None
		assigned_driver: DF.Link | None
		assigned_nurse: DF.Link | None
		clinic: DF.Link
		date: DF.Date
		departure_time: DF.Time | None
		distance_travelled_km: DF.Data | None
		end_time: DF.Datetime | None
		notes: DF.SmallText | None
		project: DF.Link
		site: DF.Link
		start_time: DF.Datetime | None
		status: DF.Literal["Planned", "In Progress", "Completed"]
		vehicle: DF.Link | None
	# end: auto-generated types

	pass
