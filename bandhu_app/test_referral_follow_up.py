import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from bandhu_app.bandhu_app.page.referral_follow_up.referral_follow_up import get_follow_up_list, log_follow_up

HELPLINE_ROLE = "Helpline Staff"


def make_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(role)
	return email


class IntegrationTestHelpline(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.helpline_user = make_user("test.helpline@bandhuapp.test", HELPLINE_ROLE)
		cls.driver_user = make_user("test.helpline.driver@bandhuapp.test", "Clinic Assistant cum Driver")
		cls.gender = frappe.get_all("Gender", limit=1, pluck="name")[0]

	def setUp(self):
		self.patient = frappe.get_doc(
			{
				"doctype": "Patient",
				"first_name": "Test Helpline Patient",
				"sex": self.gender,
				"mobile": "9876500011",
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def make_referral(self, created_days_ago=0, status="Pending", helpline_flag=1):
		return (
			frappe.get_doc(
				{
					"doctype": "Referral",
					"patient": self.patient.name,
					"referred_to": "General Hospital Ernakulam",
					"reason": "Suspected TB",
					"priority": "High",
					"status": status,
					"helpline_flag": helpline_flag,
					"created_on": add_days(frappe.utils.now_datetime(), -created_days_ago),
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def listed_names(self):
		return [referral.name for referral in get_follow_up_list()["referrals"]]

	def test_open_flagged_referrals_are_listed_due_first(self):
		newer = self.make_referral(created_days_ago=1)
		older = self.make_referral(created_days_ago=5)
		closed = self.make_referral(status="Completed")
		not_flagged = self.make_referral(helpline_flag=0)

		frappe.set_user(self.helpline_user)
		names = self.listed_names()

		self.assertLess(names.index(older), names.index(newer))
		self.assertNotIn(closed, names)
		self.assertNotIn(not_flagged, names)
		listed = next(row for row in get_follow_up_list()["referrals"] if row.name == older)
		self.assertEqual(listed.patient_name, self.patient.patient_name)
		self.assertEqual(listed.mobile, "9876500011")

	def test_a_follow_up_is_logged_and_moves_the_case_to_its_next_date(self):
		referral = self.make_referral(created_days_ago=3)
		next_date = add_days(today(), 7)

		frappe.set_user(self.helpline_user)
		log_follow_up(
			referral,
			summary="Patient has not visited the hospital yet.",
			next_followup_date=next_date,
			required_action_from="Clinic",
		)

		saved = frappe.get_doc("Referral", referral)
		self.assertEqual(saved.status, "In Progress")
		self.assertEqual(saved.required_action_from, "Clinic")
		self.assertEqual(len(saved.referral_followup), 1)
		self.assertEqual(saved.referral_followup[0].summary, "Patient has not visited the hospital yet.")
		self.assertEqual(getdate(saved.referral_followup[0].followup_date), getdate(today()))
		listed = next(row for row in get_follow_up_list()["referrals"] if row.name == referral)
		self.assertEqual(listed.due_date, getdate(next_date))

		new_case = self.make_referral()
		names = self.listed_names()
		self.assertLess(names.index(new_case), names.index(referral))

	def test_closing_a_case_takes_it_off_the_list_and_stops_further_calls(self):
		referral = self.make_referral()

		frappe.set_user(self.helpline_user)
		log_follow_up(referral, summary="Treatment completed, patient cured.", status="Completed")

		self.assertEqual(frappe.db.get_value("Referral", referral, "status"), "Completed")
		self.assertNotIn(referral, self.listed_names())
		with self.assertRaises(frappe.ValidationError):
			log_follow_up(referral, summary="Called again.", next_followup_date=add_days(today(), 1))

	def test_a_follow_up_needs_a_summary_and_a_future_next_date(self):
		referral = self.make_referral()

		frappe.set_user(self.helpline_user)
		with self.assertRaises(frappe.ValidationError):
			log_follow_up(referral, summary="  ", next_followup_date=add_days(today(), 1))
		with self.assertRaises(frappe.ValidationError):
			log_follow_up(referral, summary="No answer.")
		with self.assertRaises(frappe.ValidationError):
			log_follow_up(referral, summary="No answer.", next_followup_date=add_days(today(), -1))

		self.assertEqual(frappe.get_doc("Referral", referral).referral_followup, [])

	def test_staff_without_the_helpline_role_are_refused(self):
		referral = self.make_referral()

		frappe.set_user(self.driver_user)
		with self.assertRaises(frappe.PermissionError):
			get_follow_up_list()
		with self.assertRaises(frappe.PermissionError):
			log_follow_up(referral, summary="Called.", next_followup_date=add_days(today(), 1))

	def test_an_unknown_status_or_team_is_refused(self):
		referral = self.make_referral()

		frappe.set_user(self.helpline_user)
		with self.assertRaises(frappe.ValidationError):
			log_follow_up(referral, summary="Called.", status="Pending")
		with self.assertRaises(frappe.ValidationError):
			log_follow_up(
				referral,
				summary="Called.",
				next_followup_date=add_days(today(), 1),
				required_action_from="Pharmacy",
			)

		self.assertEqual(frappe.get_doc("Referral", referral).referral_followup, [])

	def test_saving_the_referral_directly_cannot_change_the_case_details(self):
		referral = self.make_referral()

		frappe.set_user(self.helpline_user)
		referral_doc = frappe.get_doc("Referral", referral)
		referral_doc.referred_to = "Somewhere else"
		with self.assertRaises(frappe.ValidationError):
			referral_doc.save()

		self.assertEqual(
			frappe.db.get_value("Referral", referral, "referred_to"), "General Hospital Ernakulam"
		)

	def test_saving_the_referral_directly_cannot_remove_an_earlier_call(self):
		referral = self.make_referral()

		frappe.set_user(self.helpline_user)
		log_follow_up(referral, summary="First call.", next_followup_date=add_days(today(), 2))
		referral_doc = frappe.get_doc("Referral", referral)
		referral_doc.set("referral_followup", [])
		with self.assertRaises(frappe.ValidationError):
			referral_doc.save()

		self.assertEqual(len(frappe.get_doc("Referral", referral).referral_followup), 1)

	def test_saving_the_referral_directly_cannot_reopen_a_closed_case(self):
		referral = self.make_referral()

		frappe.set_user(self.helpline_user)
		log_follow_up(referral, summary="Patient cured.", status="Completed")
		referral_doc = frappe.get_doc("Referral", referral)
		referral_doc.status = "In Progress"
		with self.assertRaises(frappe.ValidationError):
			referral_doc.save()

		self.assertEqual(frappe.db.get_value("Referral", referral, "status"), "Completed")
