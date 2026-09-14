frappe.query_reports["Bandhu PHI Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "phcchc",
			label: __("PHC/CHC"),
			fieldtype: "Data",
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
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Bandhu Projects",
		},
	],
};
