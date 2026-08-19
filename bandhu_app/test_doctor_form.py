# Copyright (c) 2026, CMID and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.bandhu_app.page.doctor_form.doctor_form import (
	complete_encounter,
	get_patient_registration_details,
	get_session_status,
	order_test,
	prescribe_medicine,
)

TEST_APPOINTMENT_TYPE = "General Consultation"
TEST_PROJECT = "CMID-Migrant-Health-2026"
TEST_SITE = "Perumbavoor-Evening-Session-Site"
TEST_CLINIC = "Bandhu Mobile Clinic Unit 1"
TEST_ITEM = "_Test Stock Item"


class TestDoctorForm(IntegrationTestCase):
	def setUp(self):
		self.today = frappe.utils.today()

		self.patient = self._make_patient("Doctor Form Test Patient")
		self.doctor_user_1 = self._make_user("doctor-form-test-1@example.com", ["Doctor"])
		self.doctor_user_2 = self._make_user("doctor-form-test-2@example.com", ["Doctor"])
		self.plain_user = self._make_user("doctor-form-test-plain@example.com", [])

		self.practitioner_1 = self._make_practitioner("Doc One", self.doctor_user_1)
		self.practitioner_2 = self._make_practitioner("Doc Two", self.doctor_user_2)

		self.session_1 = self._make_session(self.practitioner_1)
		self.session_2 = self._make_session(self.practitioner_2)

		self.encounter = self._make_encounter(self.session_1, "Waiting for Doctor")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _make_patient(self, first_name):
		return frappe.get_doc(
			{
				"doctype": "Patient",
				"first_name": first_name,
				"sex": "Male",
				"custom_height_m": 1.7,
				"custom_weight_kg": 65,
			}
		).insert(ignore_permissions=True)

	def _make_user(self, email, roles):
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
		else:
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		if roles:
			user.add_roles(*roles)
		return user.name

	def _make_practitioner(self, first_name, user_id, custom_role="Doctor"):
		return frappe.get_doc(
			{
				"doctype": "Healthcare Practitioner",
				"first_name": first_name,
				"user_id": user_id,
				"custom_role": custom_role,
			}
		).insert(ignore_permissions=True)

	def _make_session(self, practitioner):
		return frappe.get_doc(
			{
				"doctype": "Bandhu Clinic Session",
				"date": self.today,
				"project": TEST_PROJECT,
				"site": TEST_SITE,
				"clinic": TEST_CLINIC,
				"status": "In Progress",
				"assigned_doctor": practitioner.name,
			}
		).insert(ignore_permissions=True)

	def _make_encounter(self, session, workflow_state):
		return frappe.get_doc(
			{
				"doctype": "Patient Encounter",
				"patient": self.patient.name,
				"practitioner": session.assigned_doctor,
				"encounter_date": self.today,
				"encounter_time": frappe.utils.nowtime(),
				"appointment_type": TEST_APPOINTMENT_TYPE,
				"custom_clinic_session": session.name,
				"custom_workflow_state": workflow_state,
			}
		).insert(ignore_permissions=True)

	def test_order_test_writes_rows_and_advances_state(self):
		frappe.set_user(self.doctor_user_1)
		order_test(self.encounter.name, ["Malaria", "Hb"], notes="Fasting sample")

		self.encounter.reload()
		self.assertEqual(self.encounter.custom_workflow_state, "Awaiting Test")
		self.assertEqual(len(self.encounter.custom_test_instructions), 2)
		self.assertEqual({r.test_name for r in self.encounter.custom_test_instructions}, {"Malaria", "Hb"})
		self.assertEqual(self.encounter.custom_test_instructions[0].notes, "Fasting sample")

		stage = frappe.db.get_value("Patient Queue", {"encounter": self.encounter.name}, "current_stage")
		self.assertEqual(stage, "With Nurse (Test)")

	def test_order_test_rejects_unknown_test_name(self):
		frappe.set_user(self.doctor_user_1)
		with self.assertRaises(frappe.ValidationError):
			order_test(self.encounter.name, ["Not A Real Test"])

	def test_order_test_rejects_empty_list(self):
		frappe.set_user(self.doctor_user_1)
		with self.assertRaises(frappe.ValidationError):
			order_test(self.encounter.name, [])

	def test_prescribe_medicine_writes_rows_and_advances_state(self):
		frappe.set_user(self.doctor_user_1)
		prescribe_medicine(
			self.encounter.name,
			[{"medicines": TEST_ITEM, "dosage_frequency": "BD", "duration_days": 5, "quantity": 10}],
		)

		self.encounter.reload()
		self.assertEqual(self.encounter.custom_workflow_state, "Awaiting Medicine")
		self.assertEqual(len(self.encounter.custom_bandhu_prescription), 1)
		row = self.encounter.custom_bandhu_prescription[0]
		self.assertEqual(row.medicines, TEST_ITEM)
		self.assertEqual(row.dosage_frequency, "BD")
		self.assertFalse(row.dispensed)

	def test_prescribe_medicine_rejects_row_without_medicine(self):
		frappe.set_user(self.doctor_user_1)
		with self.assertRaises(frappe.ValidationError):
			prescribe_medicine(self.encounter.name, [{"dosage_frequency": "BD"}])

	def test_complete_encounter_records_diagnosis(self):
		frappe.set_user(self.doctor_user_1)
		complete_encounter(self.encounter.name, diagnosis="Viral fever", clinical_notes="Rest advised")

		self.encounter.reload()
		self.assertEqual(self.encounter.custom_workflow_state, "Completed")
		self.assertEqual(len(self.encounter.custom_bandhu_diagnosis), 1)
		self.assertEqual(self.encounter.custom_bandhu_diagnosis[0].diagnosis_name, "Viral fever")
		self.assertEqual(self.encounter.custom_bandhu_clinical_notes, "Rest advised")

	def test_complete_encounter_without_diagnosis_is_allowed(self):
		frappe.set_user(self.doctor_user_1)
		complete_encounter(self.encounter.name)
		self.encounter.reload()
		self.assertEqual(self.encounter.custom_workflow_state, "Completed")

	def test_doctor_cannot_act_on_another_doctors_patient(self):
		frappe.set_user(self.doctor_user_2)
		with self.assertRaises(frappe.PermissionError):
			order_test(self.encounter.name, ["Malaria"])

	def test_plain_user_is_blocked(self):
		frappe.set_user(self.plain_user)
		with self.assertRaises(frappe.PermissionError):
			order_test(self.encounter.name, ["Malaria"])

	def test_get_patient_registration_details_returns_cad_fields(self):
		frappe.set_user(self.doctor_user_1)
		details = get_patient_registration_details(self.encounter.name)
		self.assertEqual(details.custom_height_m, 1.7)
		self.assertEqual(details.custom_weight_kg, 65)

	def test_get_patient_registration_details_blocks_unowned_encounter(self):
		frappe.set_user(self.doctor_user_2)
		with self.assertRaises(frappe.PermissionError):
			get_patient_registration_details(self.encounter.name)

	def test_get_session_status_returns_active_session(self):
		frappe.set_user(self.doctor_user_1)
		status = get_session_status()
		self.assertTrue(status["has_session"])
		self.assertEqual(status["session_name"], self.session_1.name)
		self.assertEqual(status["status"], "In Progress")

	def test_get_session_status_no_practitioner_linked(self):
		user = self._make_user("doctor-form-test-no-practitioner@example.com", ["Doctor"])
		frappe.set_user(user)
		try:
			status = get_session_status()
		finally:
			frappe.set_user("Administrator")
		self.assertFalse(status["has_session"])
		self.assertEqual(status["message"], "No Healthcare Practitioner linked to your account.")

	def test_get_session_status_no_session_scheduled(self):
		user = self._make_user("doctor-form-test-no-session@example.com", ["Doctor"])
		self._make_practitioner("Doc No Session", user)
		frappe.set_user(user)
		try:
			status = get_session_status()
		finally:
			frappe.set_user("Administrator")
		self.assertFalse(status["has_session"])
		self.assertEqual(
			status["message"], "No session scheduled for today. Please contact Programme Manager."
		)

	def test_get_session_status_blocks_non_doctor_role(self):
		frappe.set_user(self.plain_user)
		try:
			status = get_session_status()
		finally:
			frappe.set_user("Administrator")
		self.assertFalse(status["has_session"])
		self.assertEqual(status["message"], "You do not have the Doctor role.")
