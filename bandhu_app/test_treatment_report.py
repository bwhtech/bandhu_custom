# Copyright (c) 2026, CMID and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, formatdate, nowtime, today

from bandhu_app.bandhu_app.report.bandhu_treatment_report.bandhu_treatment_report import execute
from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestTreatmentReport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		baseline = ensure_baseline_fixtures()
		cls.clinic = baseline["clinic"]
		cls.project = baseline["project"]
		cls.appointment_type = baseline["appointment_type"]
		cls.item = baseline["item"]
		cls.unit = baseline["unit"]
		cls.gender = frappe.get_all("Gender", limit=1, pluck="name")[0]

		cls.doctor = (
			frappe.get_doc(
				{
					"doctype": "Healthcare Practitioner",
					"first_name": "Treatment Report Doctor",
					"status": "Active",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		cls.value_test = (
			frappe.get_doc(
				{
					"doctype": "Bandhu Test",
					"test_name": f"Treatment Report Haemoglobin {frappe.generate_hash(length=6)}",
					"result_shape": "Value",
					"unit": "g/dL",
					"enabled": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def setUp(self):
		self.patient = self.make_patient()
		self.clinic_id = frappe.db.get_value("Patient", self.patient, "custom_bandhu_id")

		location = frappe.get_doc(
			{
				"doctype": "Bandhu Location",
				"location_name": f"Treatment Report Panchayat {frappe.generate_hash(length=6)}",
				"lsg": "Treatment Report Panchayat",
				"district": "Ernakulam",
				"state": "Kerala",
			}
		).insert(ignore_permissions=True)
		site = frappe.get_doc(
			{
				"doctype": "Site",
				"site_name": f"Treatment Report Worksite {frappe.generate_hash(length=6)}",
				"location": location.name,
			}
		).insert(ignore_permissions=True)

		self.session = frappe.get_doc(
			{
				"doctype": "Bandhu Clinic Session",
				"date": today(),
				"site": site.name,
				"clinic": self.clinic,
				"unit": self.unit,
				"project": self.project,
				"assigned_doctor": self.doctor,
				"status": "Completed",
			}
		).insert(ignore_permissions=True)

	def make_patient(self):
		return (
			frappe.get_doc(
				{
					"doctype": "Patient",
					"first_name": f"Treatment Report Patient {frappe.generate_hash(length=8)}",
					"sex": self.gender,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_visit(self, date=None, patient=None, **fields):
		return frappe.get_doc(
			{
				"doctype": "Patient Encounter",
				"patient": patient or self.patient,
				"practitioner": self.doctor,
				"encounter_date": date or today(),
				"encounter_time": nowtime(),
				"appointment_type": self.appointment_type,
				"custom_clinic_session": self.session.name,
				"custom_workflow_state": "Completed",
				**fields,
			}
		).insert(ignore_permissions=True)

	def run_report(self, **filters):
		filters.setdefault("clinic_id", self.clinic_id)
		return execute(filters)

	def test_lists_diagnosis_tests_medicines_and_referral_as_rows(self):
		visit = self.make_visit(
			custom_bandhu_diagnosis=[{"diagnosis_name": "Malaria"}],
			custom_test_instructions=[{"test_name": "Malaria", "result_type": "Positive"}],
			custom_bandhu_prescription=[
				{
					"medicines": self.item,
					"dosage_frequency": "BD",
					"duration_days": 5,
					"quantity": 10,
					"dispensed": 1,
				}
			],
		)
		frappe.get_doc(
			{
				"doctype": "Referral",
				"patient": self.patient,
				"patient_encounter": visit.name,
				"referred_to": "General Hospital Ernakulam",
				"reason": "Severe malaria",
				"priority": "High",
				"status": "Pending",
			}
		).insert(ignore_permissions=True)

		rows = self.run_report()[1]
		self.assertEqual([row["section"] for row in rows], ["Diagnosis", "Test", "Medicine", "Referral"])
		self.assertEqual(rows[1]["result"], "Positive")
		self.assertEqual(rows[2]["detail"], "BD, 5 days, Qty 10")
		self.assertEqual(rows[2]["status"], "Dispensed")
		self.assertEqual(rows[3]["item"], "General Hospital Ernakulam")
		self.assertEqual(rows[3]["detail"], "Severe malaria, High priority")

	def test_value_test_shows_the_reading_with_its_unit(self):
		self.make_visit(
			custom_test_instructions=[
				{"test_name": self.value_test, "result_type": "Value", "result_value": "11.2"},
				{"test_name": "Dengue"},
			]
		)

		rows = self.run_report()[1]
		self.assertEqual(rows[0]["item"], f"{self.value_test} (g/dL)")
		self.assertEqual(rows[0]["result"], "11.2 g/dL")
		self.assertEqual(rows[1]["result"], "Pending")

	def test_defaults_to_the_latest_visit(self):
		yesterday = add_days(today(), -1)
		self.make_visit(date=yesterday, custom_bandhu_diagnosis=[{"diagnosis_name": "Scabies"}])
		self.make_visit(custom_bandhu_diagnosis=[{"diagnosis_name": "Fever"}])

		self.assertEqual([row["item"] for row in self.run_report()[1]], ["Fever"])

	def test_summary_shows_the_follow_up_date(self):
		follow_up = add_days(today(), 10)
		self.make_visit(custom_follow_up_date=follow_up)

		self.assertIn(f"Follow-up Date:</b> {formatdate(follow_up)}", self.run_report()[2])

	def test_chosen_visit_must_belong_to_the_patient(self):
		someone_else = self.make_visit(patient=self.make_patient())

		self.assertRaises(frappe.ValidationError, self.run_report, visit=someone_else.name)

	def test_escapes_what_was_typed_into_the_visit_notes(self):
		visit = self.make_visit(custom_blood_pressure="120/80")
		frappe.db.set_value(
			"Patient Encounter",
			visit.name,
			"custom_chief_complaints",
			"<img src=x onerror=alert(1)>",
			update_modified=False,
		)

		message = self.run_report()[2]
		self.assertIn("&lt;img src=x onerror=alert(1)&gt;", message)
		self.assertNotIn("<img", message)
		self.assertIn("BP 120/80", message)

	def test_refuses_a_blank_clinic_id(self):
		self.assertRaises(frappe.ValidationError, execute, {"clinic_id": "  "})

	def test_doctor_only_opens_patients_from_their_own_session(self):
		user = self.make_user("Doctor")
		own_session = frappe.copy_doc(self.session)
		own_session.update({"assigned_doctor": self.make_practitioner(user), "status": "In Progress"})
		own_session.insert(ignore_permissions=True)
		self.make_visit(custom_clinic_session=own_session.name)
		stranger = self.make_patient()
		self.make_visit(patient=stranger)
		stranger_clinic_id = frappe.db.get_value("Patient", stranger, "custom_bandhu_id")

		with self.set_user(user):
			self.assertIn("Treatment Report Patient", self.run_report()[2])
			self.assertRaises(frappe.PermissionError, self.run_report, clinic_id=stranger_clinic_id)

	def test_system_manager_opens_any_patient(self):
		self.make_visit()

		with self.set_user(self.make_user("System Manager")):
			self.assertIn("Treatment Report Patient", self.run_report()[2])

	def make_user(self, role):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"treatment-report-{frappe.generate_hash(length=8)}@example.com",
				"first_name": "Treatment Report User",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		user.add_roles(role)
		return user.name

	def make_practitioner(self, user):
		return (
			frappe.get_doc(
				{
					"doctype": "Healthcare Practitioner",
					"first_name": "Treatment Report Session Doctor",
					"user_id": user,
					"custom_role": "Doctor",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
