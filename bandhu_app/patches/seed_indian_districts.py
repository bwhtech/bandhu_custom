import json
from pathlib import Path

import frappe

DISTRICTS_FILE = Path(__file__).with_name("india_districts.json")


def execute():
	districts_by_state = json.loads(DISTRICTS_FILE.read_text())
	existing = set()
	stateless = {}
	for name, district_name, state in frappe.get_all(
		"District", fields=["name", "district_name", "state"], as_list=True
	):
		key = (district_name or "").strip().lower()
		if state:
			existing.add((key, state))
		else:
			stateless[key] = name

	for state, district_names in districts_by_state.items():
		if not frappe.db.exists("State", state):
			continue

		for district_name in district_names:
			key = district_name.strip().lower()
			if (key, state) in existing:
				continue
			if key in stateless:
				frappe.db.set_value("District", stateless.pop(key), "state", state)
				continue

			frappe.get_doc({"doctype": "District", "district_name": district_name, "state": state}).insert(
				ignore_permissions=True
			)
