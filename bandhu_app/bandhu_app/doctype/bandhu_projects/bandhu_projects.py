# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BandhuProjects(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		end_date: DF.Date
		funding_source: DF.Data | None
		project: DF.Data
		start_date: DF.Date
		status: DF.Literal["Active", "Completed"]
	# end: auto-generated types

	pass
