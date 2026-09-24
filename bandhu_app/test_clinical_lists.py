import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.bandhu_app.page.doctor_form.doctor_form import complete_encounter, get_clinical_options
from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures
from bandhu_app.patches.seed_services_from_visits import execute as seed_services_from_visits


def make_list_entry(doctype: str, fieldname: str, value: str) -> str:
	if frappe.db.exists(doctype, value):
		return value
	return frappe.get_doc({"doctype": doctype, fieldname: value}).insert(ignore_permissions=True).name


class IntegrationTestClinicalLists(IntegrationTestCase):
	def setUp(self):
		baseline = ensure_baseline_fixtures()
		self.appointment_type = baseline["appointment_type"]
		self.today = frappe.utils.today()

		self.category = make_list_entry("Diagnosis Category", "category_name", "Test Respiratory")
		self.service = make_list_entry("Bandhu Service", "service_name", "Test Wound Dressing")

		self.doctor_user = self.make_user("test.clinical.doctor@bandhuapp.test", ["Doctor"])
		self.nurse_user = self.make_user("test.clinical.nurse@bandhuapp.test", ["Nurse"])
		self.practitioner = frappe.get_doc(
			{
				"doctype": "Healthcare Practitioner",
				"first_name": "Test Clinical Doctor",
				"user_id": self.doctor_user,
				"custom_role": "Doctor",
			}
		).insert(ignore_permissions=True)

		self.session = frappe.get_doc(
			{
				"doctype": "Bandhu Clinic Session",
				"date": self.today,
				"project": baseline["project"],
				"site": baseline["site"],
				"unit": baseline["unit"],
				"clinic": baseline["clinic"],
				"status": "In Progress",
				"assigned_doctor": self.practitioner.name,
			}
		).insert(ignore_permissions=True)
		self.patient = frappe.get_doc(
			{"doctype": "Patient", "first_name": "Test Clinical Patient", "sex": "Male"}
		).insert(ignore_permissions=True)
		self.encounter = frappe.get_doc(
			{
				"doctype": "Patient Encounter",
				"patient": self.patient.name,
				"practitioner": self.practitioner.name,
				"encounter_date": self.today,
				"encounter_time": frappe.utils.nowtime(),
				"appointment_type": self.appointment_type,
				"custom_clinic_session": self.session.name,
				"custom_workflow_state": "Waiting for Doctor",
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

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

	def test_the_doctor_is_offered_the_categories_and_services_an_admin_keeps(self):
		frappe.set_user(self.doctor_user)
		options = get_clinical_options()

		self.assertIn(self.category, options["diagnosis_categories"])
		self.assertIn(self.service, options["services"])

	def test_staff_who_are_not_doctors_are_refused_the_lists(self):
		frappe.set_user(self.nurse_user)

		with self.assertRaises(frappe.PermissionError):
			get_clinical_options()

	def test_ticked_categories_and_services_are_saved_on_the_visit(self):
		frappe.set_user(self.doctor_user)
		complete_encounter(
			self.encounter.name,
			diagnosis="Viral fever",
			diagnosis_categories=[self.category],
			services_provided=[self.service],
		)

		self.encounter.reload()
		self.assertEqual(
			[row.diagnosis_category for row in self.encounter.custom_diagnosis_categories], [self.category]
		)
		self.assertEqual(
			[row.service_name for row in self.encounter.custom_bandhu_services_provided], [self.service]
		)
		self.assertEqual(self.encounter.custom_workflow_state, "Completed")

	def test_a_category_outside_the_list_is_refused_and_nothing_is_saved(self):
		frappe.set_user(self.doctor_user)

		with self.assertRaises(frappe.ValidationError):
			complete_encounter(self.encounter.name, diagnosis_categories=["Not On The List"])

		self.encounter.reload()
		self.assertEqual(self.encounter.custom_diagnosis_categories, [])
		self.assertEqual(self.encounter.custom_workflow_state, "Waiting for Doctor")

	def test_services_recorded_before_the_list_existed_become_list_entries(self):
		frappe.get_doc(
			{
				"doctype": "Services Provided",
				"service_name": "Test Older Service",
				"parenttype": "Patient Encounter",
				"parentfield": "custom_bandhu_services_provided",
				"parent": self.encounter.name,
			}
		).db_insert()

		seed_services_from_visits()

		self.assertTrue(frappe.db.exists("Bandhu Service", "Test Older Service"))

	def test_a_service_name_frappe_cannot_store_is_cleaned_up_and_still_links(self):
		row = frappe.get_doc(
			{
				"doctype": "Services Provided",
				"service_name": "Wound <dressing>",
				"parenttype": "Patient Encounter",
				"parentfield": "custom_bandhu_services_provided",
				"parent": self.encounter.name,
			}
		)
		row.db_insert()

		seed_services_from_visits()

		cleaned = frappe.db.get_value("Services Provided", row.name, "service_name")
		self.assertEqual(cleaned, "Wound dressing")
		self.assertTrue(frappe.db.exists("Bandhu Service", cleaned))

		self.encounter.reload()
		self.encounter.save()
