import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.bandhu_app.page.cad_form.cad_form import add_company, get_form_options
from bandhu_app.patches.seed_companies_from_patients import execute as seed_companies_from_patients

CAD_ROLE = "Clinic Assistant cum Driver"


def make_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(role)
	return email


class IntegrationTestCompanyList(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.cad_user = make_user("test.company.cad@bandhuapp.test", CAD_ROLE)
		cls.nurse_user = make_user("test.company.nurse@bandhuapp.test", "Nurse")
		cls.gender = frappe.get_all("Gender", limit=1, pluck="name")[0]

	def tearDown(self):
		frappe.set_user("Administrator")

	def make_patient(self, first_name):
		return frappe.get_doc({"doctype": "Patient", "first_name": first_name, "sex": self.gender}).insert(
			ignore_permissions=True
		)

	def test_the_front_desk_can_add_a_company_and_reuse_it(self):
		frappe.set_user(self.cad_user)
		company = add_company("Kalamassery Plywood Works")

		self.assertTrue(frappe.db.exists("Bandhu Company", company))
		self.assertEqual(add_company("Kalamassery Plywood Works"), company)
		self.assertEqual(frappe.db.count("Bandhu Company", {"company_name": "Kalamassery Plywood Works"}), 1)
		self.assertIn(company, get_form_options()["companies"])

	def test_a_blank_company_name_is_refused(self):
		frappe.set_user(self.cad_user)

		with self.assertRaises(frappe.ValidationError):
			add_company("   ")

	def test_staff_outside_the_front_desk_cannot_add_a_company(self):
		frappe.set_user(self.nurse_user)

		with self.assertRaises(frappe.PermissionError):
			add_company("Nurse Added Company")

		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Bandhu Company", "Nurse Added Company"))

	def test_a_company_typed_before_the_list_existed_becomes_a_list_entry(self):
		patient = self.make_patient("Test Company Patient")
		frappe.db.set_value(
			"Patient",
			patient.name,
			"custom_name_of_company",
			"  Aluva Steel Rolling  ",
			update_modified=False,
		)

		seed_companies_from_patients()

		self.assertTrue(frappe.db.exists("Bandhu Company", "Aluva Steel Rolling"))
		self.assertEqual(
			frappe.db.get_value("Patient", patient.name, "custom_name_of_company"), "Aluva Steel Rolling"
		)

	def test_the_same_company_typed_in_two_ways_becomes_one_entry(self):
		first = self.make_patient("Test Company Patient One")
		second = self.make_patient("Test Company Patient Two")
		for patient, typed in ((first, "Perumbavoor Timber"), (second, "perumbavoor timber")):
			frappe.db.set_value(
				"Patient", patient.name, "custom_name_of_company", typed, update_modified=False
			)

		seed_companies_from_patients()

		self.assertEqual(
			frappe.db.count("Bandhu Company", {"company_name": ["like", "%erumbavoor Timber"]}), 1
		)
		for patient in (first, second):
			self.assertEqual(
				frappe.db.get_value("Patient", patient.name, "custom_name_of_company"), "Perumbavoor Timber"
			)

	def test_running_the_seed_twice_changes_nothing_the_second_time(self):
		patient = self.make_patient("Test Company Patient Twice")
		frappe.db.set_value(
			"Patient", patient.name, "custom_name_of_company", "Angamaly Packers", update_modified=False
		)

		seed_companies_from_patients()
		modified_after_first_run = frappe.db.get_value("Bandhu Company", "Angamaly Packers", "modified")
		seed_companies_from_patients()

		self.assertEqual(frappe.db.count("Bandhu Company", {"company_name": "Angamaly Packers"}), 1)
		self.assertEqual(
			frappe.db.get_value("Bandhu Company", "Angamaly Packers", "modified"), modified_after_first_run
		)

	def test_a_company_name_frappe_cannot_store_is_left_on_the_patient(self):
		patient = self.make_patient("Test Company Patient Odd Name")
		typed = "Kochi <Steel> Works"
		frappe.db.set_value("Patient", patient.name, "custom_name_of_company", typed, update_modified=False)

		seed_companies_from_patients()

		self.assertFalse(frappe.db.exists("Bandhu Company", {"company_name": typed}))
		self.assertEqual(frappe.db.get_value("Patient", patient.name, "custom_name_of_company"), typed)
