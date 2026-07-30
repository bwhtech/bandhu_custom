# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TestResult(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		encounter: DF.Link | None
		patient: DF.Link | None
		recorded_by: DF.Link | None
		remarks: DF.SmallText | None
		result_type: DF.Literal["Positive", "Negative", "Value"]
		result_value: DF.Data | None
		status: DF.Literal["Pending", "Completed"]
		test_name: DF.Literal["Malaria", "Dengue", "Other"]
	# end: auto-generated types

	pass
