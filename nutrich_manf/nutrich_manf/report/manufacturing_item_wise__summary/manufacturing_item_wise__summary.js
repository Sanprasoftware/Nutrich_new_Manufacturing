// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

frappe.query_reports["Manufacturing item wise- summary"] = {
	filters: [
		{
			fieldname: "process_definition",
			label: __("Process Definition"),
			fieldtype: "Link",
			options: "Process Definition s",
		},
		{
			fieldname: "process_type",
			label: __("Process Type"),
			fieldtype: "Link",
			options: "Process Type s",
		},
		{
			fieldname: "process_order_id",
			label: __("Process Order ID"),
			fieldtype: "Link",
			options: "Process Order s",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Manufacturing Department s",
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
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
	],
};
