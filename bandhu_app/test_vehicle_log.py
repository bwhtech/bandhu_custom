import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from bandhu_app.bandhu_app.page.cad_form.cad_form import (
	add_fuel,
	get_session_status,
	get_vehicle_log,
	save_odometer,
)
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


def make_vehicle(license_plate: str) -> str:
	if not frappe.db.exists("UOM", "Litre"):
		frappe.get_doc({"doctype": "UOM", "uom_name": "Litre"}).insert(ignore_permissions=True)
	return (
		frappe.get_doc(
			{
				"doctype": "Vehicle",
				"license_plate": license_plate,
				"make": "Eicher",
				"model": "Pro",
				"last_odometer": 1000,
				"fuel_type": "Diesel",
				"uom": "Litre",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


class IntegrationTestVehicleLog(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.baseline = ensure_baseline_fixtures()
		cls.driver, cls.driver_user = make_driver("Test Vehicle Driver", "test.vehicle.driver@bandhuapp.test")
		cls.other_driver, cls.other_driver_user = make_driver(
			"Test Other Driver", "test.vehicle.other@bandhuapp.test"
		)
		cls.vehicle = make_vehicle("TEST VL 0001")

	def setUp(self):
		self.session = self.make_session(vehicle=self.vehicle)

	def tearDown(self):
		frappe.set_user("Administrator")

	def make_session(self, vehicle=None, clinic=None, date=None, driver=None, status="In Progress"):
		return (
			frappe.get_doc(
				{
					"doctype": "Bandhu Clinic Session",
					"date": date or today(),
					"clinic": clinic or self.baseline["clinic"],
					"site": self.baseline["site"],
					"unit": self.baseline["unit"],
					"project": self.baseline["project"],
					"assigned_driver": driver or self.driver,
					"assigned_doctor": self.baseline["doctor"],
					"vehicle": vehicle,
					"status": status,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def get_usage_logs(self, session):
		return frappe.get_all(
			"Vehicle Usage Log",
			filters={"clinic_session": session},
			fields=["vehicle", "driver", "owner", "odometer_start", "odometer_end", "distance", "start_time"],
		)

	def test_start_and_end_km_are_saved_on_one_log_with_the_distance(self):
		frappe.set_user(self.driver_user)
		save_odometer(self.session, odometer_start=1000)
		result = save_odometer(self.session, odometer_end=1042)

		logs = self.get_usage_logs(self.session)
		self.assertEqual(len(logs), 1)
		self.assertEqual(logs[0].vehicle, self.vehicle)
		self.assertEqual(logs[0].driver, self.driver)
		self.assertEqual(logs[0].owner, self.driver_user)
		self.assertEqual((logs[0].odometer_start, logs[0].odometer_end, logs[0].distance), (1000, 1042, 42))
		self.assertTrue(logs[0].start_time)
		self.assertEqual(result["reading"]["distance"], 42)

	def test_end_km_below_start_km_is_refused(self):
		frappe.set_user(self.driver_user)
		save_odometer(self.session, odometer_start=1000)

		with self.assertRaises(frappe.ValidationError):
			save_odometer(self.session, odometer_end=990)

		self.assertEqual(self.get_usage_logs(self.session)[0].odometer_end, 0)

	def test_fuel_is_linked_to_the_session_with_the_amount_worked_out(self):
		frappe.set_user(self.driver_user)
		result = add_fuel(
			self.session, quantity=20, rate=100.5, fuel_station="Indian Oil Aluva", odometer_reading=1010
		)

		fuel = frappe.get_all(
			"Vehicle Refuel Log",
			filters={"clinic_session": self.session},
			fields=["vehicle", "driver", "amount", "fuel_type", "odometer_reading"],
		)
		self.assertEqual(len(fuel), 1)
		self.assertEqual(fuel[0].vehicle, self.vehicle)
		self.assertEqual(fuel[0].driver, self.driver)
		self.assertEqual(fuel[0].amount, 2010.0)
		self.assertEqual(fuel[0].fuel_type, "Diesel")
		self.assertEqual(len(result["fuel_entries"]), 1)

	def test_zero_litres_is_refused(self):
		frappe.set_user(self.driver_user)

		with self.assertRaises(frappe.ValidationError):
			add_fuel(self.session, quantity=0, rate=100, fuel_station="Indian Oil", odometer_reading=1010)

		self.assertFalse(frappe.db.exists("Vehicle Refuel Log", {"clinic_session": self.session}))

	def test_a_driver_not_on_the_session_cannot_record_km_or_fuel(self):
		frappe.set_user(self.other_driver_user)

		with self.assertRaises(frappe.PermissionError):
			save_odometer(self.session, odometer_start=1000)
		with self.assertRaises(frappe.PermissionError):
			add_fuel(self.session, quantity=10, rate=100, fuel_station="Indian Oil", odometer_reading=1000)

		frappe.set_user("Administrator")
		self.assertEqual(self.get_usage_logs(self.session), [])

	def test_the_clinic_vehicle_is_used_when_the_session_has_none(self):
		clinic_vehicle = make_vehicle("TEST VL 0002")
		clinic = frappe.get_doc(
			{
				"doctype": "Clinic",
				"clinic_name": "Test Vehicle Log Clinic",
				"project": self.baseline["project"],
				"vehicle": clinic_vehicle,
			}
		).insert(ignore_permissions=True)
		session = self.make_session(clinic=clinic.name)

		frappe.set_user(self.driver_user)
		self.assertEqual(get_vehicle_log(session)["vehicle"], clinic_vehicle)

	def test_a_vehicle_missing_from_the_vehicle_list_is_named_in_the_error(self):
		session = self.make_session(vehicle=None)
		frappe.db.set_value("Bandhu Clinic Session", session, "vehicle", "TEST VL 9999")

		frappe.set_user(self.driver_user)
		with self.assertRaisesRegex(frappe.ValidationError, "TEST VL 9999 is not in the Vehicle list"):
			save_odometer(session, odometer_start=1000)

	def test_another_days_session_is_refused(self):
		yesterday_session = self.make_session(vehicle=self.vehicle, date=add_days(today(), -1))

		frappe.set_user(self.driver_user)
		with self.assertRaises(frappe.ValidationError):
			save_odometer(yesterday_session, odometer_end=1100)

	def test_a_driver_only_sees_and_edits_logs_of_their_own_sessions(self):
		frappe.set_user(self.driver_user)
		save_odometer(self.session, odometer_start=1000)
		log = frappe.get_doc("Vehicle Usage Log", {"clinic_session": self.session})

		frappe.set_user(self.other_driver_user)
		self.assertEqual(frappe.get_list("Vehicle Usage Log", filters={"clinic_session": self.session}), [])
		self.assertFalse(frappe.has_permission("Vehicle Usage Log", "write", doc=log))

		frappe.set_user(self.driver_user)
		self.assertTrue(frappe.has_permission("Vehicle Usage Log", "write", doc=log))

	def test_a_driver_cannot_log_fuel_for_another_drivers_session_from_the_form(self):
		frappe.set_user(self.other_driver_user)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Vehicle Refuel Log",
					"vehicle": self.vehicle,
					"clinic_session": self.session,
					"date": today(),
					"odometer_reading": 1000,
					"quantity": 10,
					"rate": 100,
					"fuel_station": "Indian Oil",
				}
			).insert()

		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Vehicle Refuel Log", {"clinic_session": self.session}))

	def test_a_log_an_admin_started_stays_editable_by_the_driver(self):
		save_odometer(self.session, odometer_start=1000)

		frappe.set_user(self.driver_user)
		save_odometer(self.session, odometer_end=1030)

		self.assertEqual(self.get_usage_logs(self.session)[0].distance, 30)

	def test_a_cancelled_session_is_refused(self):
		cancelled_session = self.make_session(vehicle=self.vehicle, status="Cancelled")

		frappe.set_user(self.driver_user)
		with self.assertRaises(frappe.ValidationError):
			save_odometer(cancelled_session, odometer_start=1000)

		self.assertEqual(self.get_usage_logs(cancelled_session), [])

	def test_a_running_session_is_shown_before_a_completed_one(self):
		driver, driver_user = make_driver("Test Two Session Driver", "test.vehicle.two@bandhuapp.test")
		self.make_session(vehicle=self.vehicle, driver=driver, status="Completed")
		running_session = self.make_session(vehicle=self.vehicle, driver=driver)

		frappe.set_user(driver_user)
		status = get_session_status()

		self.assertEqual(status["session_name"], running_session)
		self.assertEqual(status["status"], "In Progress")

	def test_todays_completed_session_stays_on_the_driver_screen(self):
		driver, driver_user = make_driver("Test Finished Driver", "test.vehicle.finished@bandhuapp.test")
		session = self.make_session(vehicle=self.vehicle, driver=driver, status="Completed")

		frappe.set_user(driver_user)
		status = get_session_status()

		self.assertTrue(status["has_session"])
		self.assertEqual(status["session_name"], session)
		self.assertEqual(status["status"], "Completed")
