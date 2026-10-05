import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.bandhu_app.page.nurse_form.nurse_form import get_intervention_options, record_vitals
from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures


class IntegrationTestOtherInterventions(IntegrationTestCase):
	def setUp(self):
		baseline = ensure_baseline_fixtures()
		self.today = frappe.utils.today()
		self.intervention = self.make_intervention("Test Wound Dressing")
		self.other_intervention = self.make_intervention("Test Counselling")

		self.nurse_user = self.make_user("test.intervention.nurse@bandhuapp.test", ["Nurse"])
		self.driver_user = self.make_user(
			"test.intervention.driver@bandhuapp.test", ["Clinic Assistant cum Driver"]
		)
		self.practitioner = self.make_practitioner("Test Intervention Nurse", self.nurse_user)

		self.session = frappe.get_doc(
			{
				"doctype": "Bandhu Clinic Session",
				"date": self.today,
				"project": baseline["project"],
				"site": baseline["site"],
				"unit": baseline["unit"],
				"clinic": baseline["clinic"],
				"status": "In Progress",
				"assigned_nurse": self.practitioner.name,
				"assigned_doctor": baseline["doctor"],
			}
		).insert(ignore_permissions=True)
		patient = frappe.get_doc(
			{"doctype": "Patient", "first_name": "Test Intervention Patient", "sex": "Male"}
		).insert(ignore_permissions=True)
		self.encounter = frappe.get_doc(
			{
				"doctype": "Patient Encounter",
				"patient": patient.name,
				"practitioner": baseline["doctor"],
				"encounter_date": self.today,
				"encounter_time": frappe.utils.nowtime(),
				"appointment_type": baseline["appointment_type"],
				"custom_clinic_session": self.session.name,
				"custom_workflow_state": "Awaiting Medicine",
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def make_intervention(self, intervention_name):
		if frappe.db.exists("Other Intervention", intervention_name):
			return intervention_name
		return (
			frappe.get_doc({"doctype": "Other Intervention", "intervention_name": intervention_name})
			.insert(ignore_permissions=True)
			.name
		)

	def make_practitioner(self, first_name, user_id):
		existing = frappe.db.get_value("Healthcare Practitioner", {"user_id": user_id}, "name")
		if existing:
			return frappe.get_doc("Healthcare Practitioner", existing)
		return frappe.get_doc(
			{
				"doctype": "Healthcare Practitioner",
				"first_name": first_name,
				"user_id": user_id,
				"custom_role": "Nurse",
			}
		).insert(ignore_permissions=True)

	def make_user(self, email, roles):
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		user = frappe.get_doc("User", email)
		if roles:
			user.add_roles(*roles)
		return user.name

	def saved_interventions(self):
		self.encounter.reload()
		return [row.intervention for row in self.encounter.custom_other_interventions]

	def test_the_nurse_is_offered_the_list_an_admin_keeps(self):
		frappe.set_user(self.nurse_user)
		options = get_intervention_options()

		self.assertIn(self.intervention, options)
		self.assertIn(self.other_intervention, options)

	def test_staff_who_are_not_nurses_are_refused_the_list(self):
		frappe.set_user(self.driver_user)

		with self.assertRaises(frappe.PermissionError):
			get_intervention_options()

	def test_ticked_interventions_are_saved_with_the_vitals(self):
		frappe.set_user(self.nurse_user)
		record_vitals(self.encounter.name, temperature=98.4, other_interventions=[self.intervention])

		self.assertEqual(self.saved_interventions(), [self.intervention])
		self.encounter.reload()
		self.assertEqual(self.encounter.custom_temperature, "98.4")

	def test_interventions_can_be_recorded_without_any_vital_sign(self):
		frappe.set_user(self.nurse_user)
		record_vitals(self.encounter.name, other_interventions=[self.other_intervention])

		self.assertEqual(self.saved_interventions(), [self.other_intervention])

	def test_saving_again_replaces_the_earlier_ticks(self):
		frappe.set_user(self.nurse_user)
		record_vitals(self.encounter.name, other_interventions=[self.intervention])
		record_vitals(self.encounter.name, other_interventions=[self.other_intervention])

		self.assertEqual(self.saved_interventions(), [self.other_intervention])

	def test_vitals_without_interventions_leave_the_earlier_ticks_alone(self):
		frappe.set_user(self.nurse_user)
		record_vitals(self.encounter.name, other_interventions=[self.intervention])
		record_vitals(self.encounter.name, pulse_rate=78)

		self.assertEqual(self.saved_interventions(), [self.intervention])

	def test_unticking_everything_clears_the_earlier_ticks(self):
		frappe.set_user(self.nurse_user)
		record_vitals(self.encounter.name, other_interventions=[self.intervention])
		record_vitals(self.encounter.name, pulse_rate=80, other_interventions=[])

		self.assertEqual(self.saved_interventions(), [])

	def test_a_blank_form_is_refused(self):
		frappe.set_user(self.nurse_user)

		with self.assertRaises(frappe.ValidationError):
			record_vitals(self.encounter.name, other_interventions=[])

	def test_a_nurse_not_on_the_session_is_refused(self):
		other_nurse = self.make_user("test.intervention.othernurse@bandhuapp.test", ["Nurse"])

		frappe.set_user(other_nurse)
		with self.assertRaises(frappe.PermissionError):
			record_vitals(self.encounter.name, other_interventions=[self.intervention])

		frappe.set_user("Administrator")
		self.assertEqual(self.saved_interventions(), [])

	def test_an_intervention_outside_the_list_is_refused(self):
		frappe.set_user(self.nurse_user)

		with self.assertRaises(frappe.ValidationError):
			record_vitals(self.encounter.name, other_interventions=["Not On The List"])

		self.assertEqual(self.saved_interventions(), [])
