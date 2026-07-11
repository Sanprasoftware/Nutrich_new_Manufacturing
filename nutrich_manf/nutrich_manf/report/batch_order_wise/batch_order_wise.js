// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

frappe.query_reports["Batch Order Wise"] = {
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
			fieldname: "batch_order_id",
			label: __("Batch Order ID"),
			fieldtype: "Link",
			options: "Batch Order s",
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
			fieldname: "stock_entry",
			label: __("Stock Entry"),
			fieldtype: "Link",
			options: "Stock Entry",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
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
