import frappe
from frappe.desk.search import search_link
from frappe.tests import IntegrationTestCase

from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures

MANAGER_ROLES = ("Director", "Programme Manager")
FILTER_LINKS = {
	"Bandhu Projects": "project",
	"Bandhu Location": "location",
	"Clinic": "clinic",
	"Site": "site",
	"Unit": "unit",
}


class IntegrationTestReportFilterLookups(IntegrationTestCase):
	def setUp(self):
		self.baseline = ensure_baseline_fixtures()

	def lookup(self, user, doctype, title):
		frappe.set_user(user)
		try:
			return {
				row["value"]: row.get("label")
				for row in search_link(doctype, title, reference_doctype="Bandhu Clinic Session")
			}
		finally:
			frappe.set_user("Administrator")

	def test_managers_see_each_filter_value_by_its_title(self):
		for role in MANAGER_ROLES:
			user = make_user(f"report.lookup.{frappe.scrub(role)}@bandhuapp.test", role)
			for doctype, baseline_key in FILTER_LINKS.items():
				name = self.baseline[baseline_key]
				title = frappe.db.get_value(doctype, name, frappe.get_meta(doctype).title_field)
				with self.subTest(role=role, doctype=doctype):
					self.assertEqual(self.lookup(user, doctype, title).get(name), title)


def make_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Report Lookup", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(role)
	return email
