// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

frappe.query_reports["Process Order Wise"] = {
	filters: [
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
			fieldname: "process_order",
			label: __("Process Order"),
			fieldtype: "Link",
			options: "Process Order s",
		},
		{
			fieldname: "process_type",
			label: __("Process Type"),
			fieldtype: "Link",
			options: "Process Type s",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (data?.row_color === "raw") {
			return `<span style="color:#cf1322;">${value}</span>`;
		}

		return value;
	},
};
