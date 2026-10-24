import frappe
from frappe.desk.search import search_link
from frappe.tests import IntegrationTestCase

from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures


class IntegrationTestPharmacistLookups(IntegrationTestCase):
	def setUp(self):
		self.baseline = ensure_baseline_fixtures()
		self.pharmacist = "pharmacist.lookup@bandhuapp.test"
		if not frappe.db.exists("User", self.pharmacist):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": self.pharmacist,
					"first_name": "Pharmacist",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", self.pharmacist).add_roles("Stock User")

	def lookup(self, doctype):
		frappe.set_user(self.pharmacist)
		try:
			return [row["value"] for row in search_link(doctype, "", reference_doctype="Stock Entry")]
		finally:
			frappe.set_user("Administrator")

	def test_a_pharmacist_can_pick_the_source_project(self):
		self.assertIn(self.baseline["project"], self.lookup("Bandhu Projects"))

	def test_a_pharmacist_can_pick_the_clinic_medicine_goes_to(self):
		self.assertIn(self.baseline["clinic"], self.lookup("Clinic"))
