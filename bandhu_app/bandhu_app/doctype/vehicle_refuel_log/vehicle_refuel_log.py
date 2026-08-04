# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class VehicleRefuelLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		bill_number: DF.Data | None
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

	pass
