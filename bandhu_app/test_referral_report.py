# Copyright (c) 2026, CMID and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime, nowtime, today

from bandhu_app.bandhu_app.report.bandhu_referral_report.bandhu_referral_report import execute
from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestReferralReport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		baseline = ensure_baseline_fixtures()
		cls.clinic = baseline["clinic"]
		cls.project = baseline["project"]
		cls.appointment_type = baseline["appointment_type"]
		cls.unit = baseline["unit"]
		cls.gender = frappe.get_all("Gender", limit=1, pluck="name")[0]

		cls.doctor = (
			frappe.get_doc(
				{
					"doctype": "Healthcare Practitioner",
					"first_name": "Referral Report Doctor",
					"status": "Active",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def setUp(self):
		self.lsg = f"Referral Report LSG {frappe.generate_hash(length=6)}"
		location = frappe.get_doc(
			{
				"doctype": "Bandhu Location",
				"location_name": f"{self.lsg} Location",
				"lsg": self.lsg,
				"district": "Ernakulam",
				"state": "Kerala",
			}
		).insert(ignore_permissions=True)
		self.site = (
			frappe.get_doc(
				{
					"doctype": "Site",
					"site_name": f"Referral Report Worksite {frappe.generate_hash(length=6)}",
					"location": location.name,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_session(self, unit=None):
		return (
			frappe.get_doc(
				{
					"doctype": "Bandhu Clinic Session",
					"date": today(),
					"clinic": self.clinic,
					"site": self.site,
					"unit": unit or self.unit,
					"project": self.project,
					"assigned_doctor": self.doctor,
					"status": "Completed",
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
					"first_name": f"Referral Report Patient {frappe.generate_hash(length=8)}",
					"sex": self.gender,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_referral(self, patient=None, session=None, encounter=None, status="Pending"):
		return frappe.get_doc(
			{
				"doctype": "Referral",
				"patient": patient or self.make_patient(),
				"patient_encounter": encounter,
				"clinic_session": session,
				"referred_to": "General Hospital Ernakulam",
				"status": status,
			}
		).insert(ignore_permissions=True)

	def run_report(self, **filters):
		filters.setdefault("from_date", today())
		filters.setdefault("to_date", today())
		filters.setdefault("lsg", self.lsg)
		return execute(filters)[1]

	def test_counts_a_person_once_across_two_referrals(self):
		session = self.make_session()
		patient = self.make_patient()
		self.make_referral(patient=patient, session=session)
		self.make_referral(patient=patient, session=session)

		row = self.run_report()[0]
		self.assertEqual(row["people_referred"], 1)
		self.assertEqual(row["referrals"], 2)

	def test_splits_referrals_by_status(self):
		session = self.make_session()
		self.make_referral(session=session, status="Pending")
		self.make_referral(session=session, status="Completed")
		self.make_referral(session=session, status="Lost")

		row = self.run_report()[0]
		self.assertEqual(
			[row["pending"], row["in_progress"], row["completed"], row["lost"]],
			[1, 0, 1, 1],
		)

	def test_uses_the_visits_session_when_the_referral_has_none(self):
		patient = self.make_patient()
		encounter = frappe.get_doc(
			{
				"doctype": "Patient Encounter",
				"patient": patient,
				"practitioner": self.doctor,
				"encounter_date": today(),
				"encounter_time": nowtime(),
				"appointment_type": self.appointment_type,
				"custom_clinic_session": self.make_session(),
				"custom_workflow_state": "Completed",
			}
		).insert(ignore_permissions=True)
		self.make_referral(patient=patient, encounter=encounter.name)

		rows = self.run_report()
		self.assertEqual([row["lsg"] for row in rows], [self.lsg])

	def test_counts_a_referral_whose_session_cannot_be_found_as_not_recorded(self):
		patient = self.make_patient()
		self.make_referral(patient=patient, session=f"Missing Session {frappe.generate_hash(length=6)}")

		rows = execute({"from_date": today(), "to_date": today(), "unit": None, "lsg": None})[1]
		unplaced = next(row for row in rows if row["unit"] == "Not recorded")
		self.assertGreaterEqual(unplaced["referrals"], 1)
		self.assertIsNone(unplaced["lsg"])

	def test_unit_filter_leaves_out_other_units(self):
		other_unit = (
			frappe.get_doc(
				{"doctype": "Unit", "unit_name": f"Referral Report Unit {frappe.generate_hash(length=6)}"}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.make_referral(session=self.make_session())
		self.make_referral(session=self.make_session(unit=other_unit))

		rows = self.run_report(unit=other_unit)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["referrals"], 1)

	def test_leaves_out_referrals_made_before_the_period(self):
		session = self.make_session()
		self.make_referral(session=session)
		earlier = self.make_referral(session=session)
		frappe.db.set_value(
			"Referral", earlier.name, "creation", add_days(now_datetime(), -40), update_modified=False
		)

		self.assertEqual(self.run_report()[0]["referrals"], 1)

	def test_rejects_a_period_longer_than_a_year(self):
		self.assertRaises(
			frappe.ValidationError,
			execute,
			{"from_date": add_days(today(), -400), "to_date": today()},
		)
