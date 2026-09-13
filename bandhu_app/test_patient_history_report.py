# Copyright (c) 2026, CMID and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowtime, today

from bandhu_app.bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures
from bandhu_app.bandhu_app.report.bandhu_patient_history_report.bandhu_patient_history_report import (
	execute,
)

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestPatientHistoryReport(IntegrationTestCase):
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
					"first_name": "History Report Doctor",
					"status": "Active",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def setUp(self):
		self.site = self.make_site("History Report Panchayat")
		self.patient = self.make_patient()
		self.clinic_id = frappe.db.get_value("Patient", self.patient, "custom_bandhu_id")

	def make_site(self, lsg):
		location = frappe.get_doc(
			{
				"doctype": "Bandhu Location",
				"location_name": f"{lsg} {frappe.generate_hash(length=6)}",
				"lsg": lsg,
				"district": "Ernakulam",
				"state": "Kerala",
			}
		).insert(ignore_permissions=True)

		return (
			frappe.get_doc(
				{
					"doctype": "Site",
					"site_name": f"History Report Worksite {frappe.generate_hash(length=6)}",
					"location": location.name,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_patient(self):
		return (
			frappe.get_doc(
				{
					"doctype": "Patient",
					"first_name": f"History Report Patient {frappe.generate_hash(length=8)}",
					"sex": self.gender,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_session(self, date=None, site=None):
		return (
			frappe.get_doc(
				{
					"doctype": "Bandhu Clinic Session",
					"date": date or today(),
					"clinic": self.clinic,
					"site": site or self.site,
					"unit": self.unit,
					"project": self.project,
					"assigned_doctor": self.doctor,
					"status": "Completed",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_encounter(self, session, date=None, patient=None, **child_tables):
		return frappe.get_doc(
			{
				"doctype": "Patient Encounter",
				"patient": patient or self.patient,
				"practitioner": self.doctor,
				"encounter_date": date or today(),
				"encounter_time": nowtime(),
				"appointment_type": self.appointment_type,
				"custom_clinic_session": session,
				"custom_workflow_state": "Completed",
				**child_tables,
			}
		).insert(ignore_permissions=True)

	def run_report(self, **filters):
		filters.setdefault("clinic_id", self.clinic_id)
		return execute(filters)[1]

	def test_lists_each_visit_newest_first(self):
		yesterday = add_days(today(), -1)
		self.make_encounter(self.make_session(yesterday), date=yesterday)
		self.make_encounter(self.make_session())

		rows = self.run_report()
		self.assertEqual([row["date"] for row in rows], [getdate(today()), getdate(yesterday)])

	def test_counts_tests_and_medicines_for_each_visit(self):
		self.make_encounter(
			self.make_session(),
			custom_test_instructions=[
				{"test_name": "Malaria", "result_type": "Negative"},
				{"test_name": "Dengue"},
			],
			custom_bandhu_prescription=[
				{"medicines": self.item, "quantity": 1, "dispensed": 1},
				{"medicines": self.item, "quantity": 2},
			],
		)

		row = self.run_report()[0]
		self.assertEqual(row["tests_ordered"], 2)
		self.assertEqual(row["tests_done"], 1)
		self.assertEqual(row["medicines_prescribed"], 2)
		self.assertEqual(row["medicines_dispensed"], 1)

	def test_shows_the_diagnosis_and_the_referral(self):
		encounter = self.make_encounter(
			self.make_session(), custom_bandhu_diagnosis=[{"diagnosis_name": "Malaria"}]
		)
		frappe.get_doc(
			{
				"doctype": "Referral",
				"patient": self.patient,
				"patient_encounter": encounter.name,
				"referred_to": "General Hospital Ernakulam",
				"status": "Pending",
			}
		).insert(ignore_permissions=True)

		row = self.run_report()[0]
		self.assertEqual(row["diagnosis"], "Malaria")
		self.assertEqual(row["referral"], "General Hospital Ernakulam (Pending)")
		self.assertEqual(row["lsg"], "History Report Panchayat")

	def test_accepts_the_clinic_id_as_printed_with_spaces(self):
		self.make_encounter(self.make_session())
		printed = " ".join([self.clinic_id[:2], self.clinic_id[2], self.clinic_id[3:5], self.clinic_id[5:]])

		self.assertEqual(len(self.run_report(clinic_id=printed)), 1)

	def test_leaves_out_other_patients_visits(self):
		session = self.make_session()
		self.make_encounter(session)
		self.make_encounter(session, patient=self.make_patient())

		self.assertEqual(len(self.run_report()), 1)

	def test_lsg_filter_leaves_out_visits_in_other_lsgs(self):
		self.make_encounter(self.make_session())
		self.make_encounter(self.make_session(site=self.make_site("History Report Municipality")))

		rows = self.run_report(lsg="History Report Panchayat")
		self.assertEqual([row["lsg"] for row in rows], ["History Report Panchayat"])

	def test_refuses_an_unknown_clinic_id(self):
		self.assertRaises(frappe.ValidationError, execute, {"clinic_id": "99 9 99 99999"})
