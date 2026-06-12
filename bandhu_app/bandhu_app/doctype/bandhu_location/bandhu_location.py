# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BandhuLocation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		district: DF.Data | None
		location_name: DF.Data | None
		lsg: DF.Data | None
		lsg_code: DF.Data | None
		phcchc: DF.Data | None
		state: DF.Data | None
	# end: auto-generated types

	pass
