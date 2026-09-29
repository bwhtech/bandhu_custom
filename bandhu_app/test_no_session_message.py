import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from bandhu_app.bandhu_app.utils.session import no_session_message
from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures


class IntegrationTestNoSessionMessage(IntegrationTestCase):
	def setUp(self):
		self.baseline = ensure_baseline_fixtures()
		self.driver = (
			frappe.get_doc(
				{
					"doctype": "Healthcare Practitioner",
					"first_name": f"Message Test Driver {frappe.generate_hash(length=6)}",
					"status": "Active",
					"custom_role": "Clinic Assistant cum Driver",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_says_todays_session_has_ended_once_it_is_closed(self):
		frappe.get_doc(
			{
				"doctype": "Bandhu Clinic Session",
				"date": today(),
				"clinic": self.baseline["clinic"],
				"site": self.baseline["site"],
				"unit": self.baseline["unit"],
				"project": self.baseline["project"],
				"assigned_driver": self.driver,
				"status": "Completed",
			}
		).insert(ignore_permissions=True)

		self.assertEqual(no_session_message("assigned_driver", self.driver), "Today's session has ended.")

	def test_without_a_session_asks_for_the_programme_manager(self):
		self.assertIn("No session scheduled", no_session_message("assigned_driver", self.driver))
