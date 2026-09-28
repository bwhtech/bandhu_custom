import json
from pathlib import Path

import frappe

DISTRICTS_FILE = Path(__file__).with_name("india_districts.json")


def execute():
	districts_by_state = json.loads(DISTRICTS_FILE.read_text())
	existing = set(frappe.get_all("District", fields=["district_name", "state"], as_list=True))

	for state, district_names in districts_by_state.items():
		if not frappe.db.exists("State", state):
			continue

		for district_name in district_names:
			if (district_name, state) in existing:
				continue

			frappe.get_doc({"doctype": "District", "district_name": district_name, "state": state}).insert(
				ignore_permissions=True
			)
