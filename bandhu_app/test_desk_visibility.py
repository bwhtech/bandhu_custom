from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.bandhu_app.utils.desk_visibility import (
	restrict_other_app_desktop_icons,
	sync_bandhu_desktop_icons,
)

PHARMACY_WORKSPACE = "Pharmacist"
FOREIGN_ICON = "Accounting"
SEEDED_ROLE = "Report Manager"


def get_icon_roles(icon_name):
	return set(
		frappe.get_all(
			"Has Role",
			filters={"parenttype": "Desktop Icon", "parent": icon_name},
			pluck="role",
		)
	)


def seed_roles(icon_name):
	icon = frappe.get_doc("Desktop Icon", icon_name)
	icon.set("roles", [{"role": SEEDED_ROLE}])
	icon.save()


class IntegrationTestDeskVisibility(IntegrationTestCase):
	def setUp(self):
		developer_mode_off = patch.dict(frappe.conf, {"developer_mode": 0})
		developer_mode_off.start()
		self.addCleanup(developer_mode_off.stop)

		seed_roles(PHARMACY_WORKSPACE)
		seed_roles(FOREIGN_ICON)

	def test_pharmacy_workspace_icon_takes_the_workspace_roles(self):
		sync_bandhu_desktop_icons()

		self.assertEqual(
			get_icon_roles(PHARMACY_WORKSPACE), {"System Manager", "Stock Manager", "Stock User"}
		)

	def test_pharmacy_workspace_icon_is_not_restricted_as_another_app(self):
		restrict_other_app_desktop_icons()

		self.assertEqual(get_icon_roles(PHARMACY_WORKSPACE), {SEEDED_ROLE})
		self.assertEqual(get_icon_roles(FOREIGN_ICON), {"Administrator"})
