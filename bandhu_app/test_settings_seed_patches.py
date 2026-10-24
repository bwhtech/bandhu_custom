import frappe
from frappe.modules.patch_handler import get_patches_from_app
from frappe.tests import IntegrationTestCase

SETTINGS_SEED_PATCHES = {
	"bandhu_app.patches.seed_offered_genders",
	"bandhu_app.patches.seed_quick_countries",
}


class IntegrationTestSettingsSeedPatches(IntegrationTestCase):
	def test_settings_seeds_run_in_patch_order_on_a_site_with_empty_settings(self):
		frappe.db.delete("Bandhu Gender Option", {"parent": "Bandhu Settings"})
		frappe.db.delete("Bandhu Quick Country", {"parent": "Bandhu Settings"})

		for patch in get_patches_from_app("bandhu_app"):
			if patch in SETTINGS_SEED_PATCHES:
				frappe.get_attr(f"{patch}.execute")()

		settings = frappe.get_single("Bandhu Settings")
		self.assertEqual([row.gender for row in settings.offered_genders], ["Male", "Female", "Other"])
		self.assertEqual([row.country for row in settings.quick_countries], ["India", "Nepal"])
