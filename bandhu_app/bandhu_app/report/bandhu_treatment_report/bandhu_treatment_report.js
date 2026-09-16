frappe.query_reports["Bandhu Treatment Report"] = {
	filters: [
		{
			fieldname: "clinic_id",
			label: __("Clinic ID"),
			fieldtype: "Data",
			reqd: 1,
		},
		{
			fieldname: "visit",
			label: __("Visit"),
			fieldtype: "Link",
			options: "Patient Encounter",
			description: __("Leave blank for the latest visit."),
		},
	],
};
