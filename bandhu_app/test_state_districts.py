# Copyright (c) 2026, CMID and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.bandhu_app.utils.state_districts import get_districts
from bandhu_app.patches.seed_indian_districts import execute as seed_indian_districts

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestStateDistricts(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.cad_user = cls.make_user("test.districts.cad@bandhuapp.test", ["Clinic Assistant cum Driver"])
		cls.no_role_user = cls.make_user("test.districts.norole@bandhuapp.test", [])

	@classmethod
	def make_user(cls, email, roles):
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
		else:
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		if roles:
			user.add_roles(*roles)

		return email

	def make_state(self):
		state_name = f"Test State {frappe.generate_hash(length=6)}"
		frappe.get_doc({"doctype": "State", "state_name": state_name}).insert(ignore_permissions=True)
		return state_name

	def make_district(self, district_name, state):
		return frappe.get_doc({"doctype": "District", "district_name": district_name, "state": state}).insert(
			ignore_permissions=True
		)

	def test_cad_gets_the_districts_recorded_for_the_state(self):
		state = self.make_state()
		self.make_district("Test Patna Nagar", state)
		self.make_district("Test Gaya Nagar", state)
		self.make_district("Test Other State District", self.make_state())

		with self.set_user(self.cad_user):
			districts = get_districts(state=state)
			filtered = get_districts(txt="patna", state=state)

		self.assertEqual(districts, ["Test Gaya Nagar", "Test Patna Nagar"])
		self.assertEqual(filtered, ["Test Patna Nagar"])

	def test_cad_gets_seeded_districts_for_a_real_state(self):
		seed_indian_districts()

		with self.set_user(self.cad_user):
			self.assertEqual(get_districts(txt="patna", state="Bihar"), ["Patna"])

	def test_no_state_returns_no_districts(self):
		with self.set_user(self.cad_user):
			self.assertEqual(get_districts(state=None), [])

	def test_same_district_name_can_exist_in_two_states(self):
		first = self.make_district("Test Hamirpur", self.make_state())
		second_state = self.make_state()
		second = self.make_district("Test Hamirpur", second_state)

		self.assertEqual(first.name, "Test Hamirpur")
		self.assertEqual(second.name, f"Test Hamirpur ({second_state})")
		self.assertEqual(second.district_name, "Test Hamirpur")

	def test_same_district_twice_in_one_state_is_rejected(self):
		state = self.make_state()
		self.make_district("Test Duplicate District", state)

		self.assertRaises(frappe.DuplicateEntryError, self.make_district, "Test Duplicate District", state)

	def test_moving_a_district_into_a_state_that_has_it_is_rejected(self):
		first_state = self.make_state()
		self.make_district("Test Moved District", first_state)
		district = self.make_district("Test Moved District", self.make_state())

		district.state = first_state
		self.assertRaises(frappe.DuplicateEntryError, district.save, ignore_permissions=True)

	def test_seed_keeps_both_districts_that_share_a_name_and_does_not_repeat(self):
		frappe.db.delete("District", {"district_name": "Hamirpur"})

		seed_indian_districts()
		count_after_first_run = frappe.db.count("District")
		seed_indian_districts()

		self.assertEqual(frappe.db.count("District"), count_after_first_run)
		hamirpur_names_by_state = dict(
			frappe.get_all(
				"District", filters={"district_name": "Hamirpur"}, fields=["state", "name"], as_list=True
			)
		)
		self.assertEqual(
			hamirpur_names_by_state,
			{"Uttar Pradesh": "Hamirpur", "Himachal Pradesh": "Hamirpur (Himachal Pradesh)"},
		)

	def test_user_without_the_cad_role_is_blocked(self):
		state = self.make_state()

		with self.set_user(self.no_role_user):
			self.assertRaises(frappe.PermissionError, get_districts, "", state)
