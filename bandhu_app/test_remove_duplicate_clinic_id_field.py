from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.patches import remove_duplicate_clinic_id_field

PATCH_MODULE = "bandhu_app.patches.remove_duplicate_clinic_id_field"


class TestRemoveDuplicateClinicIdField(IntegrationTestCase):
	def test_refuses_to_drop_a_column_that_holds_data(self):
		with (
			patch(f"{PATCH_MODULE}.frappe.db.has_column", return_value=True),
			patch(f"{PATCH_MODULE}.frappe.db.count", return_value=3),
			patch(f"{PATCH_MODULE}.frappe.db.sql_ddl") as sql_ddl,
			patch(f"{PATCH_MODULE}.frappe.delete_doc") as delete_doc,
			patch(f"{PATCH_MODULE}.frappe.log_error") as log_error,
		):
			remove_duplicate_clinic_id_field.execute()

		sql_ddl.assert_not_called()
		delete_doc.assert_not_called()
		log_error.assert_called_once()

	def test_drops_an_empty_column_once(self):
		with (
			patch(f"{PATCH_MODULE}.frappe.db.has_column", return_value=True),
			patch(f"{PATCH_MODULE}.frappe.db.count", return_value=0),
			patch(f"{PATCH_MODULE}.frappe.db.sql_ddl") as sql_ddl,
		):
			remove_duplicate_clinic_id_field.execute()

		sql_ddl.assert_called_once_with("alter table `tabPatient` drop column `custom_clinic_id`")

	def test_running_again_after_removal_changes_nothing(self):
		self.assertFalse(frappe.db.has_column("Patient", "custom_clinic_id"))

		with patch(f"{PATCH_MODULE}.frappe.db.sql_ddl") as sql_ddl:
			remove_duplicate_clinic_id_field.execute()
			remove_duplicate_clinic_id_field.execute()

		sql_ddl.assert_not_called()
		self.assertFalse(frappe.db.exists("Custom Field", "Patient-custom_clinic_id"))
