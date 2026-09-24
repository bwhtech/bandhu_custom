import re

import frappe

MAX_SERVICE_NAME_LENGTH = 140


def as_a_record_name(service_name: str) -> str:
	return re.sub(r"[<>]", "", service_name).strip()[:MAX_SERVICE_NAME_LENGTH].strip()


def execute():
	rows = frappe.get_all("Services Provided", fields=["name", "service_name"])
	existing = {service.lower(): service for service in frappe.get_all("Bandhu Service", pluck="name")}

	for row in rows:
		service_name = as_a_record_name(row.service_name or "")
		if not service_name:
			if row.service_name:
				frappe.db.set_value(
					"Services Provided", row.name, "service_name", None, update_modified=False
				)
			continue

		service = existing.get(service_name.lower())
		if not service:
			service = (
				frappe.get_doc({"doctype": "Bandhu Service", "service_name": service_name})
				.insert(ignore_permissions=True)
				.name
			)
			existing[service_name.lower()] = service

		if service != row.service_name:
			frappe.db.set_value("Services Provided", row.name, "service_name", service, update_modified=False)
