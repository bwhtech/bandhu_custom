import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures

TEAM = (
	("assigned_doctor", "Doctor", "Doctor"),
	("assigned_nurse", "Nurse", "Nurse"),
	("assigned_driver", "Clinic Assistant cum Driver", "Clinic Assistant cum Driver"),
)


class IntegrationTestSessionTeamAccess(IntegrationTestCase):
	def setUp(self):
		baseline = ensure_baseline_fixtures()
		self.team_users = {}
		session = {
			"doctype": "Bandhu Clinic Session",
			"date": today(),
			"clinic": baseline["clinic"],
			"site": baseline["site"],
			"unit": baseline["unit"],
			"project": baseline["project"],
		}
		for fieldname, practitioner_role, user_role in TEAM:
			user = make_user(f"team.access.{fieldname}@bandhuapp.test", user_role)
			session[fieldname] = make_practitioner(user, practitioner_role)
			self.team_users[fieldname] = user
		self.session = frappe.get_doc(session).insert(ignore_permissions=True)

	def test_every_team_member_with_a_practitioner_user_permission_can_read_the_session(self):
		for fieldname, user in self.team_users.items():
			with self.subTest(fieldname=fieldname):
				self.assertTrue(
					frappe.db.exists("User Permission", {"user": user, "allow": "Healthcare Practitioner"})
				)
				self.assertTrue(
					frappe.has_permission("Bandhu Clinic Session", "read", doc=self.session, user=user)
				)


def make_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Team Access", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(role)
	return email


def make_practitioner(user: str, practitioner_role: str) -> str:
	existing = frappe.db.get_value("Healthcare Practitioner", {"user_id": user})
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Healthcare Practitioner",
				"first_name": f"Team Access {practitioner_role}",
				"status": "Active",
				"custom_role": practitioner_role,
				"user_id": user,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)
