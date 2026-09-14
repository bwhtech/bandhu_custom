frappe.query_reports["Bandhu Patient History Report"] = {
	filters: [
		{
			fieldname: "clinic_id",
			label: __("Clinic ID"),
			fieldtype: "Data",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Bandhu Projects",
		},
		{
			fieldname: "lsg",
			label: __("LSG"),
			fieldtype: "Data",
		},
		{
			fieldname: "district",
			label: __("District"),
			fieldtype: "Data",
		},
	],
};
