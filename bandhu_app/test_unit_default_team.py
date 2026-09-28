import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from bandhu_app.bandhu_app.page.new_schedule.new_schedule import get_form_options
from bandhu_app.bandhu_app.page.new_session.new_session import get_form_options as get_new_session_options
from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures, make_unit_with_team

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class TestUnitDefaultTeam(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.baseline = ensure_baseline_fixtures()
		cls.team = (cls.baseline["doctor"], cls.baseline["nurse"], cls.baseline["driver"])
		cls.unit = make_unit_with_team(*cls.team)

	def new_session(self, **overrides):
		return frappe.get_doc(
			{
				"doctype": "Bandhu Clinic Session",
				"date": today(),
				"clinic": self.baseline["clinic"],
				"site": self.baseline["site"],
				"project": self.baseline["project"],
				"unit": self.unit,
				**overrides,
			}
		).insert(ignore_permissions=True)

	def test_session_without_a_team_takes_its_units_team(self):
		session = self.new_session()

		self.assertEqual(
			(session.assigned_doctor, session.assigned_nurse, session.assigned_driver), self.team
		)

	def test_a_doctor_chosen_for_the_session_is_kept_over_the_units(self):
		other_doctor = (
			frappe.get_doc(
				{
					"doctype": "Healthcare Practitioner",
					"first_name": "Stand In Doctor",
					"status": "Active",
					"custom_role": "Doctor",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		session = self.new_session(assigned_doctor=other_doctor)

		self.assertEqual((session.assigned_doctor, session.assigned_nurse), (other_doctor, self.team[1]))

	def test_schedule_and_its_sessions_take_the_units_team(self):
		schedule = frappe.get_doc(
			{
				"doctype": "Bandhu Session Schedule",
				"enabled": 1,
				"site": self.baseline["site"],
				"clinic": self.baseline["clinic"],
				"unit": self.unit,
				"frequency": "Weekly",
				"valid_from": today(),
				"weekdays": [{"weekday": weekday} for weekday in WEEKDAYS],
			}
		).insert(ignore_permissions=True)
		session = frappe.get_doc(
			"Bandhu Clinic Session",
			frappe.get_all(
				"Bandhu Clinic Session", filters={"session_schedule": schedule.name}, pluck="name"
			)[0],
		)

		self.assertEqual(
			(schedule.assigned_doctor, schedule.assigned_nurse, schedule.assigned_driver), self.team
		)
		self.assertEqual(
			(session.assigned_doctor, session.assigned_nurse, session.assigned_driver), self.team
		)

	def test_new_schedule_form_options_give_each_unit_its_team(self):
		option = next(item for item in get_form_options()["units"] if item.value == self.unit)

		self.assertEqual((option.doctor, option.nurse, option.cad), self.team)

	def test_new_session_form_options_give_each_unit_its_team(self):
		option = next(item for item in get_new_session_options()["units"] if item.value == self.unit)

		self.assertEqual((option.doctor, option.nurse, option.cad), self.team)

	def test_unit_refuses_a_practitioner_of_the_wrong_role_in_a_team_slot(self):
		doctor, nurse, _driver = self.team

		self.assertRaisesRegex(
			frappe.ValidationError,
			"must be a Healthcare Practitioner with role",
			make_unit_with_team,
			doctor,
			nurse,
			nurse,
		)
