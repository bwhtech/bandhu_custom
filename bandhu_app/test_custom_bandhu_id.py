# Copyright (c) 2026, CMID and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from bandhu_app.bandhu_app.utils.custom_bandhu_id import UNKNOWN_LSG_CODE, UNKNOWN_UNIT_CODE


class IntegrationTestCustomBandhuId(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.current_year = now_datetime().strftime("%y")

		cls.location = frappe.get_doc(
			{
				"doctype": "Bandhu Location",
				"location_name": "Clinic Id Test Location",
				"lsg_numeric_code": "77",
			}
		).insert(ignore_permissions=True)

		cls.unit = frappe.get_doc(
			{
				"doctype": "Unit",
				"unit_name": "Clinic Id Test Unit",
				"unit_numeric_code": "8",
			}
		).insert(ignore_permissions=True)

	def register(self, first_name, location=None, unit=None):
		return frappe.get_doc(
			{
				"doctype": "Patient",
				"first_name": first_name,
				"sex": "Male",
				"dob": "1990-01-01",
				"custom_registered_lsg": location,
				"custom_registered_unit": unit,
			}
		).insert(ignore_permissions=True)

	def test_id_is_ten_digits_composed_of_lsg_unit_year_and_serial(self):
		patient = self.register("Composed Id", self.location.name, self.unit.name)

		clinic_id = patient.custom_bandhu_id
		self.assertRegex(clinic_id, r"^\d{10}$")
		self.assertEqual(clinic_id[:2], "77")
		self.assertEqual(clinic_id[2], "8")
		self.assertEqual(clinic_id[3:5], self.current_year)

	def test_serial_advances_between_patients(self):
		first = self.register("Serial One", self.location.name, self.unit.name)
		second = self.register("Serial Two", self.location.name, self.unit.name)

		self.assertEqual(int(second.custom_bandhu_id[5:]), int(first.custom_bandhu_id[5:]) + 1)

	def test_registration_without_session_context_uses_reserved_codes(self):
		patient = self.register("No Origin")

		self.assertTrue(patient.custom_bandhu_id.startswith(UNKNOWN_LSG_CODE + UNKNOWN_UNIT_CODE))
		self.assertRegex(patient.custom_bandhu_id, r"^\d{10}$")

	def test_existing_id_is_never_overwritten(self):
		patient = self.register("Keeps Id", self.location.name, self.unit.name)
		issued = patient.custom_bandhu_id

		patient.first_name = "Keeps Id Renamed"
		patient.save(ignore_permissions=True)

		self.assertEqual(patient.reload().custom_bandhu_id, issued)

	def test_numeric_code_cannot_change_once_ids_are_issued(self):
		self.register("Locks Code", self.location.name, self.unit.name)

		self.location.lsg_numeric_code = "78"
		with self.assertRaises(frappe.ValidationError):
			self.location.save(ignore_permissions=True)

	def test_lsg_numeric_code_must_be_two_digits(self):
		location = frappe.get_doc({"doctype": "Bandhu Location", "location_name": "Bad Width Location"})
		location.lsg_numeric_code = "7"

		with self.assertRaises(frappe.ValidationError):
			location.insert(ignore_permissions=True)

	def test_unit_numeric_code_must_be_one_digit(self):
		unit = frappe.get_doc({"doctype": "Unit", "unit_name": "Bad Width Unit"})
		unit.unit_numeric_code = "88"

		with self.assertRaises(frappe.ValidationError):
			unit.insert(ignore_permissions=True)

	def test_qr_code_is_generated_for_the_issued_id(self):
		patient = self.register("Qr Owner", self.location.name, self.unit.name)

		qr_url = frappe.db.get_value("Patient", patient.name, "custom_qr_code")
		self.assertTrue(qr_url)
		self.assertIn(patient.custom_bandhu_id, qr_url)
