# Copyright (c) 2026, CMID and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowtime, today

from bandhu_app.bandhu_app.report.bandhu_phi_report.bandhu_phi_report import execute
from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestPHIReport(IntegrationTestCase):
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
				{"doctype": "Healthcare Practitioner", "first_name": "PHI Report Doctor", "status": "Active"}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def setUp(self):
		self.phcchc = f"PHI Report PHC {frappe.generate_hash(length=6)}"
		self.location = self.make_location("PHI Report Panchayat")
		self.site = self.make_site(self.location)

	def make_location(self, lsg):
		return (
			frappe.get_doc(
				{
					"doctype": "Bandhu Location",
					"location_name": f"{lsg} {frappe.generate_hash(length=6)}",
					"lsg": lsg,
					"district": "Ernakulam",
					"state": "Kerala",
					"phcchc": self.phcchc,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_site(self, location):
		return (
			frappe.get_doc(
				{
					"doctype": "Site",
					"site_name": f"PHI Report Worksite {frappe.generate_hash(length=6)}",
					"location": location,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_session(self, date=None, site=None, status="Completed"):
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
					"status": status,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_encounter(self, session):
		patient = (
			frappe.get_doc(
				{
					"doctype": "Patient",
					"first_name": f"PHI Report Patient {frappe.generate_hash(length=8)}",
					"sex": self.gender,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		return frappe.get_doc(
			{
				"doctype": "Patient Encounter",
				"patient": patient,
				"practitioner": self.doctor,
				"encounter_date": today(),
				"encounter_time": nowtime(),
				"appointment_type": self.appointment_type,
				"custom_clinic_session": session,
				"custom_workflow_state": "Completed",
			}
		).insert(ignore_permissions=True)

	def run_report(self, **filters):
		filters.setdefault("from_date", today())
		filters.setdefault("to_date", today())
		filters.setdefault("phcchc", self.phcchc)
		return execute(filters)[1]

	def test_sessions_on_one_day_under_one_phc_share_a_row(self):
		other_site = self.make_site(self.location)
		self.make_session()
		self.make_session(site=other_site)

		rows = self.run_report()
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["sessions_held"], 2)
		self.assertEqual(rows[0]["lsg"], "PHI Report Panchayat")
		self.assertIn(frappe.db.get_value("Site", other_site, "site_name"), rows[0]["sites"])

	def test_each_date_gets_its_own_row(self):
		self.make_session(date=add_days(today(), -1))
		self.make_session()

		rows = self.run_report(from_date=add_days(today(), -1))
		self.assertEqual([row["date"] for row in rows], [getdate(add_days(today(), -1)), getdate(today())])

	def test_planned_and_cancelled_sessions_are_not_counted(self):
		self.make_session()
		self.make_session(status="In Progress")
		self.make_session(status="Planned")
		self.make_session(status="Cancelled")

		self.assertEqual(self.run_report()[0]["sessions_held"], 2)

	def test_counts_patients_seen(self):
		session = self.make_session()
		self.make_encounter(session)
		self.make_encounter(session)

		self.assertEqual(self.run_report()[0]["patients"], 2)

	def test_lsg_filter_leaves_out_other_lsgs_under_the_same_phc(self):
		other_location = self.make_location("PHI Report Municipality")
		self.make_session()
		self.make_session(site=self.make_site(other_location))

		rows = self.run_report(lsg="PHI Report Panchayat")
		self.assertEqual([row["lsg"] for row in rows], ["PHI Report Panchayat"])

	def test_rejects_a_period_longer_than_a_year(self):
		self.assertRaises(
			frappe.ValidationError,
			execute,
			{"from_date": add_days(today(), -400), "to_date": today()},
		)
