import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.baseline_test_fixtures import ensure_baseline_fixtures


class IntegrationTestStockEntryFundingSourceAndClinic(IntegrationTestCase):
	def setUp(self):
		self.clinic = ensure_baseline_fixtures()["clinic"]
		self.funding_source = (
			frappe.get_doc(
				{
					"doctype": "Funding Source",
					"funding_source_name": f"Test Donor {frappe.generate_hash(length=8)}",
				}
			)
			.insert()
			.name
		)

	def test_receipt_without_funding_source_is_refused(self):
		stock_entry = make_stock_entry("Material Receipt")

		with self.assertRaises(frappe.MandatoryError):
			run_validate_hooks(stock_entry)

	def test_receipt_drops_issued_to_clinic(self):
		stock_entry = make_stock_entry(
			"Material Receipt",
			custom_funding_source=self.funding_source,
			custom_issued_to_clinic=self.clinic,
		)

		run_validate_hooks(stock_entry)

		self.assertEqual(stock_entry.custom_funding_source, self.funding_source)
		self.assertIsNone(stock_entry.custom_issued_to_clinic)

	def test_issue_keeps_clinic_and_drops_funding_source(self):
		stock_entry = make_stock_entry(
			"Material Issue",
			custom_funding_source=self.funding_source,
			custom_issued_to_clinic=self.clinic,
		)

		run_validate_hooks(stock_entry)

		self.assertIsNone(stock_entry.custom_funding_source)
		self.assertEqual(stock_entry.custom_issued_to_clinic, self.clinic)

	def test_manufacture_drops_both_fields(self):
		stock_entry = make_stock_entry(
			"Manufacture",
			custom_funding_source=self.funding_source,
			custom_issued_to_clinic=self.clinic,
		)

		run_validate_hooks(stock_entry)

		self.assertIsNone(stock_entry.custom_funding_source)
		self.assertIsNone(stock_entry.custom_issued_to_clinic)

	def test_transfer_drops_funding_source(self):
		stock_entry = make_stock_entry(
			"Material Transfer",
			custom_funding_source=self.funding_source,
			custom_issued_to_clinic=self.clinic,
		)

		run_validate_hooks(stock_entry)

		self.assertIsNone(stock_entry.custom_funding_source)
		self.assertEqual(stock_entry.custom_issued_to_clinic, self.clinic)


def make_stock_entry(purpose, **values):
	return frappe.get_doc({"doctype": "Stock Entry", "purpose": purpose, **values})


def run_validate_hooks(stock_entry):
	validate_hooks = (
		frappe.get_hooks("doc_events", app_name="bandhu_app").get("Stock Entry", {}).get("validate", [])
	)
	for method in validate_hooks:
		frappe.get_attr(method)(stock_entry, "validate")
