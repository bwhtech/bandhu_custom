# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Prescription(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dispensed: DF.Check
		dispensed_by: DF.Link | None
		dosage_frequency: DF.Literal["", "OD", "BD", "TID", "QID"]
		duration_days: DF.Int
		instructions: DF.SmallText | None
		medicines: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		quantity: DF.Int
		source: DF.Literal["In-House", "External"]
	# end: auto-generated types

	pass
