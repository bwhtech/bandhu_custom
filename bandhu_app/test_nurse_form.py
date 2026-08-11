# Copyright (c) 2026, CMID and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowtime, today

from bandhu_app.bandhu_app.page.nurse_form.nurse_form import (
	dispense_medicine,
	get_patient_registration_details,
	submit_test_results,
)

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

TEST_ITEM = "_Test Stock Item"


class IntegrationTestNurseForm(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.clinic = frappe.get_all("Clinic", limit=1, pluck="name")[0]
		cls.site = frappe.get_all("Site", limit=1, pluck="name")[0]
		cls.project = frappe.get_all("Bandhu Projects", limit=1, pluck="name")[0]
		cls.appointment_type = frappe.get_all("Appointment Type", limit=1, pluck="name")[0]
		cls.gender = frappe.get_all("Gender", limit=1, pluck="name")[0]

		cls.nurse_practitioner = cls._make_practitioner("Test Nurse Alpha", "Nurse")
		cls.other_practitioner = cls._make_practitioner("Test Nurse Beta", "Nurse")

		cls.nurse_user = cls._make_user(
			"test.nurse.alpha@bandhuapp.test", cls.nurse_practitioner, ["Nurse"]
		)
		cls.other_nurse_user = cls._make_user(
			"test.nurse.beta@bandhuapp.test", cls.other_practitioner, ["Nurse"]
		)
		cls.no_role_user = cls._make_user("test.norole@bandhuapp.test", None, [])

		cls.session = cls._make_session(cls.nurse_practitioner)
		cls.other_session = cls._make_session(cls.other_practitioner)

	@classmethod
	def _make_practitioner(cls, first_name, custom_role=None):
		doc = frappe.get_doc(
			{
				"doctype": "Healthcare Practitioner",
				"first_name": first_name,
				"status": "Active",
				"custom_role": custom_role,
			}
		).insert(ignore_permissions=True)
		return doc.name

	@classmethod
	def _make_user(cls, email, practitioner, roles):
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

		if practitioner:
			frappe.db.set_value("Healthcare Practitioner", practitioner, "user_id", email)

		return email

	@classmethod
	def _make_session(cls, assigned_nurse):
		doc = frappe.get_doc(
			{
				"doctype": "Bandhu Clinic Session",
				"date": today(),
				"clinic": cls.clinic,
				"site": cls.site,
				"project": cls.project,
				"assigned_nurse": assigned_nurse,
				"status": "In Progress",
			}
		).insert(ignore_permissions=True)
		return doc.name

	@classmethod
	def _make_patient(cls, first_name, **fields):
		doc = frappe.get_doc(
			{
				"doctype": "Patient",
				"first_name": first_name,
				"sex": cls.gender,
				**fields,
			}
		).insert(ignore_permissions=True)
		return doc.name

	def _make_encounter(self, session, workflow_state, practitioner=None, tests=None, prescriptions=None, patient_fields=None):
		patient = self._make_patient(f"Test Patient {frappe.generate_hash(length=8)}", **(patient_fields or {}))
		doc = frappe.get_doc(
			{
				"doctype": "Patient Encounter",
				"patient": patient,
				"practitioner": practitioner or self.nurse_practitioner,
				"encounter_date": today(),
				"encounter_time": nowtime(),
				"appointment_type": self.appointment_type,
				"custom_clinic_session": session,
				"custom_workflow_state": workflow_state,
				"custom_test_instructions": tests or [],
				"custom_bandhu_prescription": prescriptions or [],
			}
		).insert(ignore_permissions=True)
		return doc

	def test_submit_test_results_writes_results_and_advances_state(self):
		encounter = self._make_encounter(
			self.session, "Awaiting Test", tests=[{"test_name": "Malaria", "notes": "Fasting"}]
		)
		row_name = encounter.custom_test_instructions[0].name

		frappe.set_user(self.nurse_user)
		try:
			result = submit_test_results(
				encounter.name, [{"name": row_name, "result_type": "Negative", "result_value": ""}]
			)
		finally:
			frappe.set_user("Administrator")

		self.assertTrue(result["success"])
		encounter.reload()
		self.assertEqual(encounter.custom_workflow_state, "Awaiting Doctor Review")
		self.assertEqual(encounter.custom_test_instructions[0].result_type, "Negative")
		self.assertEqual(
			frappe.db.get_value("Patient Queue", {"encounter": encounter.name}, "current_stage"),
			"With Doctor",
		)

	def test_submit_test_results_rejects_wrong_state(self):
		encounter = self._make_encounter(
			self.session, "Waiting for Doctor", tests=[{"test_name": "Malaria"}]
		)
		row_name = encounter.custom_test_instructions[0].name

		frappe.set_user(self.nurse_user)
		try:
			self.assertRaises(
				frappe.ValidationError,
				submit_test_results,
				encounter.name,
				[{"name": row_name, "result_type": "Negative"}],
			)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(
			frappe.db.get_value("Patient Encounter", encounter.name, "custom_workflow_state"),
			"Waiting for Doctor",
		)

	def test_dispense_medicine_marks_rows_and_completes(self):
		encounter = self._make_encounter(
			self.session,
			"Awaiting Medicine",
			prescriptions=[{"medicines": TEST_ITEM, "dosage_frequency": "OD", "quantity": 5}],
		)
		row_name = encounter.custom_bandhu_prescription[0].name

		frappe.set_user(self.nurse_user)
		try:
			result = dispense_medicine(encounter.name, [row_name])
		finally:
			frappe.set_user("Administrator")

		self.assertTrue(result["success"])
		encounter.reload()
		self.assertEqual(encounter.custom_workflow_state, "Completed")
		self.assertTrue(encounter.custom_bandhu_prescription[0].dispensed)
		self.assertEqual(encounter.custom_bandhu_prescription[0].dispensed_by, self.nurse_practitioner)

		queue_row = frappe.db.get_value(
			"Patient Queue", {"encounter": encounter.name}, ["current_stage", "status"], as_dict=True
		)
		self.assertEqual(queue_row.current_stage, "Completed")
		self.assertEqual(queue_row.status, "Done")

	def test_dispense_medicine_allows_partial_dispense(self):
		encounter = self._make_encounter(
			self.session,
			"Awaiting Medicine",
			prescriptions=[
				{"medicines": TEST_ITEM, "dosage_frequency": "OD", "quantity": 5},
				{"medicines": TEST_ITEM, "dosage_frequency": "BD", "quantity": 3},
			],
		)
		dispensed_row = encounter.custom_bandhu_prescription[0].name

		frappe.set_user(self.nurse_user)
		try:
			dispense_medicine(encounter.name, [dispensed_row])
		finally:
			frappe.set_user("Administrator")

		encounter.reload()
		self.assertTrue(encounter.custom_bandhu_prescription[0].dispensed)
		self.assertFalse(encounter.custom_bandhu_prescription[1].dispensed)

	def test_unprivileged_user_is_blocked(self):
		test_encounter = self._make_encounter(self.session, "Awaiting Test", tests=[{"test_name": "Hb"}])
		medicine_encounter = self._make_encounter(
			self.session, "Awaiting Medicine", prescriptions=[{"medicines": TEST_ITEM}]
		)

		frappe.set_user(self.no_role_user)
		try:
			self.assertRaises(
				frappe.PermissionError,
				submit_test_results,
				test_encounter.name,
				[{"name": test_encounter.custom_test_instructions[0].name, "result_type": "Negative"}],
			)
			self.assertRaises(
				frappe.PermissionError,
				dispense_medicine,
				medicine_encounter.name,
				[medicine_encounter.custom_bandhu_prescription[0].name],
			)
		finally:
			frappe.set_user("Administrator")

	def test_nurse_not_assigned_to_session_is_blocked(self):
		encounter = self._make_encounter(
			self.other_session, "Awaiting Test", practitioner=self.other_practitioner, tests=[{"test_name": "Hb"}]
		)

		frappe.set_user(self.nurse_user)
		try:
			self.assertRaises(
				frappe.PermissionError,
				submit_test_results,
				encounter.name,
				[{"name": encounter.custom_test_instructions[0].name, "result_type": "Negative"}],
			)
		finally:
			frappe.set_user("Administrator")

	def test_get_patient_registration_details_returns_cad_fields(self):
		encounter = self._make_encounter(
			self.session, "Awaiting Test", patient_fields={"custom_height_m": 1.6, "custom_weight_kg": 55}
		)

		frappe.set_user(self.nurse_user)
		try:
			details = get_patient_registration_details(encounter.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(details.custom_height_m, 1.6)
		self.assertEqual(details.custom_weight_kg, 55)
