# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


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

	pass
