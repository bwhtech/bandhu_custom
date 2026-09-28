import re

import frappe

MAX_COMPANY_NAME_LENGTH = 140


def is_usable_as_a_record_name(company_name: str) -> bool:
	return len(company_name) <= MAX_COMPANY_NAME_LENGTH and not re.search(r"[<>]", company_name)


def execute():
	recorded = frappe.get_all(
		"Patient",
		filters={"custom_name_of_company": ["is", "set"]},
		fields=["name", "custom_name_of_company"],
	)
	existing = {company.lower(): company for company in frappe.get_all("Bandhu Company", pluck="name")}
	unusable = []

	for patient in recorded:
		company_name = (patient.custom_name_of_company or "").strip()
		if not company_name:
			continue

		if not is_usable_as_a_record_name(company_name):
			unusable.append(f"{patient.name}: {company_name[:200]}")
			continue

		company = existing.get(company_name.lower())
		if not company:
			company = (
				frappe.get_doc({"doctype": "Bandhu Company", "company_name": company_name})
				.insert(ignore_permissions=True)
				.name
			)
			existing[company_name.lower()] = company

		if company != patient.custom_name_of_company:
			frappe.db.set_value(
				"Patient", patient.name, "custom_name_of_company", company, update_modified=False
			)

	if unusable:
		frappe.log_error(
			title="Company names left as typed",
			message="\n".join(unusable),
		)
