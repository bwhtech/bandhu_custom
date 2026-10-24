import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowtime, today

from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures
from bandhu_app.patches import cancel_visits_left_open_in_closed_sessions


class IntegrationTestCancelVisitsLeftOpen(IntegrationTestCase):
	def setUp(self):
		self.baseline = ensure_baseline_fixtures()
		self.gender = frappe.get_all("Gender", limit=1, pluck="name")[0]

	def make_session(self, status):
		return (
			frappe.get_doc(
				{
					"doctype": "Bandhu Clinic Session",
					"date": add_days(today(), -1) if status == "Completed" else today(),
					"clinic": self.baseline["clinic"],
					"site": self.baseline["site"],
					"unit": self.baseline["unit"],
					"project": self.baseline["project"],
					"status": status,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_visit(self, session, workflow_state):
		patient = frappe.get_doc(
			{
				"doctype": "Patient",
				"first_name": f"Left Open {frappe.generate_hash(length=6)}",
				"sex": self.gender,
			}
		).insert(ignore_permissions=True)
		visit = frappe.get_doc(
			{
				"doctype": "Patient Encounter",
				"patient": patient.name,
				"practitioner": self.baseline["doctor"],
				"encounter_date": today(),
				"encounter_time": nowtime(),
				"appointment_type": self.baseline["appointment_type"],
				"custom_clinic_session": session,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Patient Encounter", visit.name, "custom_workflow_state", workflow_state)
		return visit.name

	def workflow_state(self, visit):
		return frappe.db.get_value("Patient Encounter", visit, "custom_workflow_state")

	def test_an_open_visit_in_a_closed_session_is_cancelled(self):
		visit = self.make_visit(self.make_session("Completed"), "Awaiting Doctor Review")

		cancel_visits_left_open_in_closed_sessions.execute()

		self.assertEqual(self.workflow_state(visit), "Cancelled")

	def test_a_running_session_and_finished_visits_are_left_alone(self):
		running = self.make_visit(self.make_session("In Progress"), "Waiting for Doctor")
		finished = self.make_visit(self.make_session("Completed"), "Completed")

		cancel_visits_left_open_in_closed_sessions.execute()

		self.assertEqual(self.workflow_state(running), "Waiting for Doctor")
		self.assertEqual(self.workflow_state(finished), "Completed")
