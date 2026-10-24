# Copyright (c) 2026, CMID and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

MAX_HORIZON_DAYS = 730


class BandhuSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from bandhu_app.bandhu_app.doctype.bandhu_gender_option.bandhu_gender_option import BandhuGenderOption
		from bandhu_app.bandhu_app.doctype.bandhu_quick_country.bandhu_quick_country import BandhuQuickCountry

		disable_auto_session_generation: DF.Check
		offered_genders: DF.Table[BandhuGenderOption]
		quick_countries: DF.Table[BandhuQuickCountry]
		session_horizon_days: DF.Int
	# end: auto-generated types

	def validate(self):
		# An unbounded horizon would have the nightly job create sessions for every
		# site until the end of time on its first run.
		if self.session_horizon_days and self.session_horizon_days > MAX_HORIZON_DAYS:
			frappe.throw(_("Sessions cannot be generated more than {0} days ahead.").format(MAX_HORIZON_DAYS))

		countries = [row.country for row in self.quick_countries]
		for country in set(countries):
			if countries.count(country) > 1:
				frappe.throw(_("{0} is listed more than once in Quick Pick Countries.").format(country))

		seen_genders = set()
		for row in self.offered_genders:
			if row.gender in seen_genders:
				frappe.throw(_("{0} is listed more than once in Genders Offered.").format(row.gender))
			seen_genders.add(row.gender)


def get_offered_genders() -> list[str]:
	return [row.gender for row in frappe.get_single("Bandhu Settings").offered_genders]
