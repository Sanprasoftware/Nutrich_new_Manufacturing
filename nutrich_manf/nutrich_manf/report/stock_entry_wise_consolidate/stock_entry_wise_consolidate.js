// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Entry Wise Consolidate"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
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
			fieldname: "batch_order_id",
			label: __("Batch Order ID"),
			fieldtype: "Link",
			options: "Batch Order s",
		},
		{
			fieldname: "stock_entry",
			label: __("Stock Entry"),
			fieldtype: "Link",
			options: "Stock Entry",
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "item_code",
			label: __("Stock Item"),
			fieldtype: "Link",
			options: "Item",
		},
	],
};
