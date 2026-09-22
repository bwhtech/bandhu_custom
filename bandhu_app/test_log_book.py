import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_time, today

from bandhu_app.bandhu_app.page.cad_form.cad_form import get_log_book, save_log_book
from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures

DRIVER_ROLE = "Clinic Assistant cum Driver"


def make_driver(first_name: str, email: str) -> tuple[str, str]:
	practitioner = frappe.get_doc(
		{
			"doctype": "Healthcare Practitioner",
			"first_name": first_name,
			"status": "Active",
			"custom_role": DRIVER_ROLE,
		}
	).insert(ignore_permissions=True)

	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": first_name, "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(DRIVER_ROLE)
	frappe.db.set_value("Healthcare Practitioner", practitioner.name, "user_id", email)
	return practitioner.name, email


class IntegrationTestLogBook(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.baseline = ensure_baseline_fixtures()
		cls.driver, cls.driver_user = make_driver(
			"Test Log Book Driver", "test.logbook.driver@bandhuapp.test"
		)
		cls.other_driver, cls.other_driver_user = make_driver(
			"Test Log Book Other", "test.logbook.other@bandhuapp.test"
		)

	def setUp(self):
		self.session = self.make_session()

	def tearDown(self):
		frappe.set_user("Administrator")

	def make_session(self, date=None, status="Planned"):
		return (
			frappe.get_doc(
				{
					"doctype": "Bandhu Clinic Session",
					"date": date or today(),
					"clinic": self.baseline["clinic"],
					"site": self.baseline["site"],
					"unit": self.baseline["unit"],
					"project": self.baseline["project"],
					"assigned_driver": self.driver,
					"assigned_doctor": self.baseline["doctor"],
					"status": status,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def get_saved_log_book(self, session):
		return frappe.db.get_value(
			"Bandhu Clinic Session",
			session,
			["departure_time", "arrival_time", "distance_travelled_km"],
			as_dict=True,
		)

	def test_departure_arrival_and_distance_are_saved_on_the_session(self):
		frappe.set_user(self.driver_user)
		result = save_log_book(
			self.session, departure_time="08:15", arrival_time="09:05", distance_travelled_km=18.5
		)

		saved = self.get_saved_log_book(self.session)
		self.assertEqual(get_time(saved.departure_time), get_time("08:15:00"))
		self.assertEqual(get_time(saved.arrival_time), get_time("09:05:00"))
		self.assertEqual(saved.distance_travelled_km, "18.5")
		self.assertEqual(result["distance_travelled_km"], "18.5")

	def test_saving_the_arrival_later_keeps_the_departure(self):
		frappe.set_user(self.driver_user)
		save_log_book(self.session, departure_time="08:15")
		save_log_book(self.session, arrival_time="09:05", distance_travelled_km=12)

		saved = self.get_saved_log_book(self.session)
		self.assertEqual(get_time(saved.departure_time), get_time("08:15:00"))
		self.assertEqual(saved.distance_travelled_km, "12")

	def test_arrival_before_departure_is_refused(self):
		frappe.set_user(self.driver_user)
		save_log_book(self.session, departure_time="09:00")

		with self.assertRaises(frappe.ValidationError):
			save_log_book(self.session, arrival_time="08:30")

		self.assertIsNone(self.get_saved_log_book(self.session).arrival_time)

	def test_a_negative_distance_is_refused(self):
		frappe.set_user(self.driver_user)

		with self.assertRaises(frappe.ValidationError):
			save_log_book(self.session, distance_travelled_km=-5)

		self.assertFalse(self.get_saved_log_book(self.session).distance_travelled_km)

	def test_arrival_before_departure_in_one_save_is_refused(self):
		frappe.set_user(self.driver_user)

		with self.assertRaises(frappe.ValidationError):
			save_log_book(self.session, departure_time="09:00", arrival_time="08:30")

		self.assertIsNone(self.get_saved_log_book(self.session).departure_time)

	def test_an_unreadable_time_is_refused_with_a_message(self):
		frappe.set_user(self.driver_user)

		for value in ("", "late"):
			with self.assertRaisesRegex(frappe.ValidationError, "Enter a valid time"):
				save_log_book(self.session, departure_time=value)

	def test_an_impossible_distance_is_refused(self):
		frappe.set_user(self.driver_user)

		for distance in (float("inf"), float("nan"), 1000000):
			with self.assertRaises(frappe.ValidationError):
				save_log_book(self.session, distance_travelled_km=distance)

		self.assertFalse(self.get_saved_log_book(self.session).distance_travelled_km)

	def test_a_driver_not_on_the_session_cannot_read_or_fill_the_log_book(self):
		frappe.set_user(self.other_driver_user)

		with self.assertRaises(frappe.PermissionError):
			get_log_book(self.session)
		with self.assertRaises(frappe.PermissionError):
			save_log_book(self.session, departure_time="08:15")

		frappe.set_user("Administrator")
		self.assertIsNone(self.get_saved_log_book(self.session).departure_time)

	def test_a_closed_or_past_session_is_refused(self):
		completed_session = self.make_session(status="Completed")
		past_session = self.make_session(date=add_days(today(), -1))

		frappe.set_user(self.driver_user)
		for session in (completed_session, past_session):
			with self.assertRaises(frappe.ValidationError):
				save_log_book(session, departure_time="08:15")
