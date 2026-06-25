// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

// frappe.query_reports["Item Wise Tracking"] = {
// 	filters: [
// 		// {
// 		// 	"fieldname": "my_filter",
// 		// 	"label": __("My Filter"),
// 		// 	"fieldtype": "Data",
// 		// 	"reqd": 1,
// 		// },
// 	],
// };
 

frappe.query_reports["Item Wise Tracking"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "item_group",
            label: __("Item Group"),
            fieldtype: "Link",
            options: "Item Group"
        },
        {
            fieldname: "item_code",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item"
        },
        {
            fieldname: "cost_center",
            label: __("Cost Center"),
            fieldtype: "Link",
            options: "Cost Center"
        },
        {
            fieldname: "warehouse_group",
            label: __("Warehouse Group"),
            fieldtype: "Link",
            options: "Warehouse",
            get_query: function() {
                return {
                    filters: {
                        is_group: 1
                    }
                };
            }
        },
        {
            fieldname: "warehouse",
            label: __("Warehouse"),
            fieldtype: "Link",
            options: "Warehouse",
            get_query: function() {
                return {
                    filters: {
                        is_group: 0
                    }
                };
            }
        },
        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project"
        }
    ]
};