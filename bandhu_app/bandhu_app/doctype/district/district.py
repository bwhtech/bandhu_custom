# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class District(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		district_name: DF.Data
		state: DF.Link
	# end: auto-generated types

	def autoname(self):
		self.name = self.district_name
		if frappe.db.exists("District", self.name):
			self.name = f"{self.district_name} ({self.state})"

	def validate(self):
		duplicate = frappe.db.exists(
			"District",
			{"district_name": self.district_name, "state": self.state, "name": ("!=", self.name)},
		)
		if duplicate:
			frappe.throw(
				_("District {0} already exists in {1}.").format(self.district_name, self.state),
				frappe.DuplicateEntryError,
			)


def on_doctype_update():
	frappe.db.add_unique("District", ["district_name", "state"])
