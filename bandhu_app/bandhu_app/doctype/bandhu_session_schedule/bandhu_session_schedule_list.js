// Copyright (c) 2026, CMID and contributors
// For license information, please see license.txt

frappe.listview_settings["Bandhu Session Schedule"] = {
	// Adding a schedule goes through the guided page; the raw form stays for editing.
	primary_action: function () {
		frappe.set_route("new-schedule");
	},
};
