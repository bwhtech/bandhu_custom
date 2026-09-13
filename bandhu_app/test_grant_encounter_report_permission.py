# Copyright (c) 2026, CMID and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.patches.grant_encounter_report_permission import execute

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestGrantEncounterReportPermission(IntegrationTestCase):
	def test_system_manager_can_run_reports_on_visits(self):
		execute()
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"encounter-report-{frappe.generate_hash(length=8)}@example.com",
				"first_name": "Encounter Report Manager",
				"send_welcome_email": 0,
				"roles": [{"role": "System Manager"}],
			}
		).insert(ignore_permissions=True)

		self.assertTrue(frappe.has_permission("Patient Encounter", "report", user=user.name))

	def test_running_twice_adds_one_rule_and_keeps_the_others(self):
		other_rules = frappe.get_all(
			"Custom DocPerm",
			filters={"parent": "Patient Encounter", "role": ["!=", "System Manager"]},
			fields=["role", "permlevel", "read", "report"],
			order_by="role asc, permlevel asc",
		)

		execute()
		execute()

		self.assertEqual(
			frappe.db.count("Custom DocPerm", {"parent": "Patient Encounter", "role": "System Manager"}), 1
		)
		self.assertEqual(
			frappe.get_all(
				"Custom DocPerm",
				filters={"parent": "Patient Encounter", "role": ["!=", "System Manager"]},
				fields=["role", "permlevel", "read", "report"],
				order_by="role asc, permlevel asc",
			),
			other_rules,
		)
