import frappe
from frappe.desk.search import search_link
from frappe.tests import IntegrationTestCase

CAD_ROLE = "Clinic Assistant cum Driver"


def make_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(role)
	return email


def new_company(company_name: str):
	return frappe.get_doc({"doctype": "Bandhu Company", "company_name": company_name})


class IntegrationTestCompanyList(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.cad_user = make_user("test.company.cad@bandhuapp.test", CAD_ROLE)
		cls.nurse_user = make_user("test.company.nurse@bandhuapp.test", "Nurse")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_the_front_desk_finds_a_company_by_part_of_its_name(self):
		company = new_company("Kalamassery Plywood Works").insert(ignore_permissions=True).name

		frappe.set_user(self.cad_user)
		matches = [row["value"] for row in search_link("Bandhu Company", "Plywood")]

		self.assertIn(company, matches)

	def test_the_front_desk_can_add_a_company(self):
		frappe.set_user(self.cad_user)
		company = new_company("Aluva Steel Rolling").insert().name

		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value("Bandhu Company", company, "company_name"), "Aluva Steel Rolling"
		)

	def test_staff_outside_the_front_desk_cannot_add_a_company(self):
		frappe.set_user(self.nurse_user)

		with self.assertRaises(frappe.PermissionError):
			new_company("Nurse Added Company").insert()

		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Bandhu Company", "Nurse Added Company"))
