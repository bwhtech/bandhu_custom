import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures, make_site_in_location
from bandhu_app.patches import fill_session_lsg_and_phc_chc

EMPTY_LOCATION = {"location": None, "lsg": None, "phc_chc": None}


class TestFillSessionLsgAndPhcChc(IntegrationTestCase):
	def test_fills_sessions_and_schedules_saved_before_the_fields_existed(self):
		baseline = ensure_baseline_fixtures()
		site = make_site_in_location("LSG Patch Test Site", "Perumbavoor Municipality", "THQH Perumbavoor")
		common = {"clinic": baseline["clinic"], "site": site, "unit": baseline["unit"]}
		session = frappe.get_doc(
			{"doctype": "Bandhu Clinic Session", "date": today(), "project": baseline["project"], **common}
		).insert(ignore_permissions=True)
		schedule = frappe.get_doc(
			{
				"doctype": "Bandhu Session Schedule",
				"enabled": 0,
				"frequency": "Weekly",
				"valid_from": today(),
				"weekdays": [{"weekday": "Monday"}],
				**common,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Bandhu Clinic Session", session.name, EMPTY_LOCATION)
		frappe.db.set_value("Bandhu Session Schedule", schedule.name, EMPTY_LOCATION)

		fill_session_lsg_and_phc_chc.execute()

		expected = ("Perumbavoor Municipality", "THQH Perumbavoor")
		self.assertEqual(
			frappe.db.get_value("Bandhu Clinic Session", session.name, ["lsg", "phc_chc"]), expected
		)
		self.assertEqual(
			frappe.db.get_value("Bandhu Session Schedule", schedule.name, ["lsg", "phc_chc"]), expected
		)
