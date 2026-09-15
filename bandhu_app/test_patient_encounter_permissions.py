import json
from pathlib import Path

import frappe
from frappe.modules.utils import sync_customizations_for_doctype
from frappe.tests import IntegrationTestCase

CUSTOM_FOLDER = Path(frappe.get_app_path("bandhu_app", "bandhu_app", "custom"))


class TestPatientEncounterPermissions(IntegrationTestCase):
	def sync_permissions_from_json(self):
		customizations = json.loads((CUSTOM_FOLDER / "patient_encounter.json").read_text())
		sync_customizations_for_doctype(
			{
				"doctype": "Patient Encounter",
				"custom_fields": [],
				"property_setters": [],
				"custom_perms": customizations["custom_perms"],
			},
			str(CUSTOM_FOLDER),
		)
		frappe.clear_cache(doctype="Patient Encounter")

	def make_system_manager(self):
		return (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"encounter-report-{frappe.generate_hash(length=8)}@example.com",
					"first_name": "Encounter Report Manager",
					"send_welcome_email": 0,
					"roles": [{"role": "System Manager"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_system_manager_keeps_report_access_after_a_customization_sync(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Patient Encounter", "role": "System Manager"})
		self.sync_permissions_from_json()

		self.assertTrue(frappe.has_permission("Patient Encounter", "report", user=self.make_system_manager()))

	def test_sync_leaves_system_manager_read_only_on_visits(self):
		self.sync_permissions_from_json()

		system_manager = self.make_system_manager()
		self.assertTrue(frappe.has_permission("Patient Encounter", "read", user=system_manager))
		self.assertFalse(frappe.has_permission("Patient Encounter", "write", user=system_manager))
