# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class VehicleRefuelLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		bill_number: DF.Data | None
		clinic_session: DF.Link | None
		date: DF.Date
		driver: DF.Link | None
		fill_type: DF.Literal["Full Tank", "Partial"]
		fuel_station: DF.Data
		fuel_type: DF.Literal["Petrol", "Diesel", "CNG", "Electric"]
		odometer_reading: DF.Int
		quantity: DF.Float
		rate: DF.Currency
		time: DF.Time | None
		vehicle: DF.Link
	# end: auto-generated types

	def validate(self):
		if flt(self.quantity) <= 0 or flt(self.rate) <= 0:
			frappe.throw(_("Litres and rate must be more than zero."))

		if cint(self.odometer_reading) < 0:
			frappe.throw(_("A km reading cannot be negative."))

		self.amount = flt(flt(self.quantity) * flt(self.rate), self.precision("amount"))
