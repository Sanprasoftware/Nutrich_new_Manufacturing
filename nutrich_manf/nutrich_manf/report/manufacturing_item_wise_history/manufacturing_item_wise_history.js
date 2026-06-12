// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

frappe.query_reports["Manufacturing item wise-history"] = {
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

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) {
			return value;
		}

		const color_map = {
			raw: "#cf1322",
			finish: "#389e0d",
			scrap: "#ad8b00",
		};
		let color = null;

		if (column.fieldname.startsWith("definition_")) {
			color = color_map[data.definition_row_color];
		} else if (column.fieldname.startsWith("order_")) {
			color = color_map[data.order_row_color];
		} else if (column.fieldname.startsWith("batch_")) {
			color = color_map[data.batch_row_color];
		} else if (column.fieldname.startsWith("stock_")) {
			color = color_map[data.stock_row_color];
		}

		if (!color) {
			return value;
		}

		return `<span style="color:${color};">${value}</span>`;
	},
};
