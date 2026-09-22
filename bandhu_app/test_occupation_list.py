import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from bandhu_app.bandhu_app.page.cad_form.cad_form import get_form_options, register_patient
from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures

CAD_ROLE = "Clinic Assistant cum Driver"


def make_occupation(occupation_name: str, is_major: int) -> str:
	if frappe.db.exists("Occupation", occupation_name):
		frappe.db.set_value("Occupation", occupation_name, "is_major_occupation", is_major)
		return occupation_name
	return (
		frappe.get_doc(
			{
				"doctype": "Occupation",
				"occupation_name": occupation_name,
				"is_major_occupation": is_major,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


class IntegrationTestOccupationList(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.baseline = ensure_baseline_fixtures()
		cls.gender = frappe.get_all("Gender", limit=1, pluck="name")[0]
		cls.sector = frappe.get_all("Sectors", limit=1, pluck="name")[0]
		cls.major_occupation = make_occupation("Test Construction Worker", 1)
		cls.other_occupation = make_occupation("Test Boat Crew", 0)

		cls.practitioner = frappe.get_doc(
			{
				"doctype": "Healthcare Practitioner",
				"first_name": "Test Occupation CAD",
				"status": "Active",
				"custom_role": CAD_ROLE,
			}
		).insert(ignore_permissions=True)
		cls.cad_user = "test.occupation.cad@bandhuapp.test"
		if not frappe.db.exists("User", cls.cad_user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": cls.cad_user,
					"first_name": "Test Occupation CAD",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", cls.cad_user).add_roles(CAD_ROLE)
		frappe.db.set_value("Healthcare Practitioner", cls.practitioner.name, "user_id", cls.cad_user)

		cls.session = (
			frappe.get_doc(
				{
					"doctype": "Bandhu Clinic Session",
					"date": today(),
					"clinic": cls.baseline["clinic"],
					"site": cls.baseline["site"],
					"unit": cls.baseline["unit"],
					"project": cls.baseline["project"],
					"assigned_driver": cls.practitioner.name,
					"assigned_doctor": cls.baseline["doctor"],
					"status": "In Progress",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_major_occupations_are_offered_as_buttons_and_the_rest_in_the_picker(self):
		frappe.set_user(self.cad_user)
		options = get_form_options()

		self.assertIn(self.major_occupation, options["major_occupations"])
		self.assertIn(self.other_occupation, options["other_occupations"])
		self.assertNotIn(self.other_occupation, options["major_occupations"])

	def test_occupation_and_sector_are_saved_on_their_own_fields(self):
		frappe.set_user(self.cad_user)
		patient = register_patient(
			full_name="Test Occupation Patient",
			sex=self.gender,
			age=30,
			occupation=self.major_occupation,
			sector=self.sector,
			session=self.session,
		)

		saved = frappe.get_doc("Patient", patient)
		self.assertEqual(saved.custom_occupation, self.major_occupation)
		self.assertEqual(saved.custom_sector_of_employment, self.sector)

	def test_a_value_that_is_only_a_sector_is_refused_as_an_occupation(self):
		frappe.set_user(self.cad_user)

		with self.assertRaises(frappe.ValidationError):
			register_patient(
				full_name="Test Unknown Occupation Patient",
				sex=self.gender,
				age=30,
				occupation=self.sector,
				session=self.session,
			)

		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Patient", {"first_name": "Test Unknown Occupation Patient"}))
