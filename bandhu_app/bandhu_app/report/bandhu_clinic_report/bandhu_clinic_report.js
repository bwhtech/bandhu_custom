frappe.query_reports["Bandhu Clinic Report"] = {
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
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["Clinic", "Project", "Unit", "LSG", "Site"],
			default: "Clinic",
			reqd: 1,
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Bandhu Projects",
		},
		{
			fieldname: "location",
			label: __("LSG / Location"),
			fieldtype: "Link",
			options: "Bandhu Location",
		},
		{
			fieldname: "site",
			label: __("Site"),
			fieldtype: "Link",
			options: "Site",
		},
		{
			fieldname: "unit",
			label: __("Unit"),
			fieldtype: "Link",
			options: "Unit",
		},
		{
			fieldname: "clinic",
			label: __("Clinic"),
			fieldtype: "Link",
			options: "Clinic",
		},
	],
};
