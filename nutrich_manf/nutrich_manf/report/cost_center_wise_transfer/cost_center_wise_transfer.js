// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

frappe.query_reports["Cost Center Wise Transfer"] = {
	onload: function (report) {
		set_fiscal_year_dates(report);
	},
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: frappe.sys_defaults.fiscal_year,
			on_change: function () {
				set_fiscal_year_dates();
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.sys_defaults.year_start_date || frappe.datetime.year_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.sys_defaults.year_end_date || frappe.datetime.year_end(),
		},
		{
			fieldname: "account",
			label: __("Account"),
			fieldtype: "Link",
			options: "Account",
			get_query: function () {
				return {
					filters: {
						company: frappe.query_report.get_filter_value("company"),
						is_group: 0,
					},
				};
			},
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
			get_query: function () {
				return {
					filters: {
						company: frappe.query_report.get_filter_value("company"),
					},
				};
			},
		},
	],
};

function set_fiscal_year_dates(report) {
	report = report || frappe.query_report;
	const fiscal_year = report.get_filter_value("fiscal_year");

	if (!fiscal_year) {
		return;
	}

	frappe.db
		.get_value("Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"])
		.then((response) => {
			const fiscal_year_dates = response.message;

			if (!fiscal_year_dates) {
				return;
			}

			report.set_filter_value({
				from_date: fiscal_year_dates.year_start_date,
				to_date: fiscal_year_dates.year_end_date,
			});
		});
}
