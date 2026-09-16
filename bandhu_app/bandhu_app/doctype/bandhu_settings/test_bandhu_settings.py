import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.patches.seed_offered_genders import execute as seed_offered_genders


def set_offered_genders(test_case, genders):
	settings = frappe.get_single("Bandhu Settings")
	original_genders = [row.gender for row in settings.offered_genders]
	settings.set("offered_genders", [{"gender": gender} for gender in genders])
	settings.save()
	test_case.addCleanup(restore_offered_genders, original_genders)


def restore_offered_genders(genders):
	settings = frappe.get_single("Bandhu Settings")
	settings.set("offered_genders", [{"gender": gender} for gender in genders])
	settings.save()


def saved_offered_genders():
	return [row.gender for row in frappe.get_single("Bandhu Settings").offered_genders]


class IntegrationTestBandhuSettings(IntegrationTestCase):
	def test_seed_offered_genders_fills_an_empty_list(self):
		self.addCleanup(restore_offered_genders, saved_offered_genders())
		frappe.db.delete("Bandhu Gender Option", {"parent": "Bandhu Settings"})

		seed_offered_genders()

		self.assertEqual(saved_offered_genders(), ["Male", "Female", "Other"])

	def test_seed_offered_genders_keeps_the_list_an_admin_set(self):
		set_offered_genders(self, ["Female"])

		seed_offered_genders()

		self.assertEqual(saved_offered_genders(), ["Female"])

	def test_same_gender_twice_is_rejected(self):
		self.assertRaisesRegex(
			frappe.ValidationError, "listed more than once", set_offered_genders, self, ["Male", "Male"]
		)

	def test_empty_gender_list_is_rejected(self):
		self.assertRaises(frappe.MandatoryError, set_offered_genders, self, [])
