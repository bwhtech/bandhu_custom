# Copyright (c) 2026, CMID and Contributors
# See license.txt

from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_months, add_years, today

from bandhu_app.bandhu_app.utils.patient import compact_age

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestPatient(IntegrationTestCase):
	def test_adult_age_is_whole_years(self):
		self.assertEqual(compact_age(add_days(add_years(today(), -47), -60)), "47y")

	def test_birthday_not_yet_reached_this_year_rounds_down(self):
		self.assertEqual(compact_age(add_days(add_years(today(), -30), 1)), "29y")

	def test_infant_under_a_year_reads_in_months(self):
		self.assertEqual(compact_age(add_months(today(), -8)), "8mo")

	def test_newborn_reads_in_days(self):
		self.assertEqual(compact_age(add_days(today(), -12)), "12d")

	def test_missing_or_future_dob_is_blank(self):
		self.assertEqual(compact_age(None), "")
		self.assertEqual(compact_age(""), "")
		self.assertEqual(compact_age(add_days(today(), 1)), "")
