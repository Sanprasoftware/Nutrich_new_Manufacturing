# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.data import getdate

from erpnext.accounts.report.financial_statements import get_cost_centers_with_children


DIVISION_TRANSFER_ACCOUNTS = [
	"CASHEW  DIVISION - NFPL",
	"EXPORT DIVISION - NFPL",
	"MAIN DIVISION - NFPL",
	"WHOLESALE DIVISION - NFPL",
	"TRADING DIVISION - NFPL",
	"RETAIL DIVISION",
]

CREDIT_BALANCE_ROOTS = {"Liability", "Equity", "Income"}


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	accounts = get_division_transfer_accounts(filters.company)
	balances = get_cost_center_balances(filters, accounts)
	cost_centers = get_report_cost_centers(filters, balances)
	columns = get_columns(cost_centers)
	data = get_data(accounts, balances, cost_centers)
	return columns, data


def validate_filters(filters: frappe._dict):
	if not filters.company:
		frappe.throw(_("Company is required"))
	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year is required"))

	year_dates = frappe.db.get_value(
		"Fiscal Year",
		filters.fiscal_year,
		["year_start_date", "year_end_date"],
		as_dict=True,
	)
	if not year_dates:
		frappe.throw(_("Invalid Fiscal Year"))

	filters.from_date = year_dates.year_start_date
	filters.to_date = year_dates.year_end_date
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("Fiscal Year start date cannot be after end date"))


def col(label, fieldname, fieldtype="Currency", options=None, width=130):
	column = {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
	if options:
		column["options"] = options
	return column


def get_columns(cost_centers: list[str]) -> list[dict]:
	columns = [col("Account", "account", "Link", "Account", 260)]
	for cost_center in cost_centers:
		columns.append(col(cost_center, fieldname_for(cost_center), "Currency", width=160))
	columns.append(col("Total", "total", "Currency", width=160))
	return columns


def get_data(accounts: list[frappe._dict], balances: dict[str, dict[str, float]], cost_centers: list[str]) -> list[dict]:
	data = []

	for account in accounts:
		row = {"account": account.name or account.label}
		total = 0

		for cost_center in cost_centers:
			amount = flt(balances.get(account.name, {}).get(cost_center))
			if account.root_type in CREDIT_BALANCE_ROOTS:
				amount *= -1

			row[fieldname_for(cost_center)] = amount
			total += amount

		row["total"] = total
		data.append(row)

	return data


def get_division_transfer_accounts(company: str) -> list[frappe._dict]:
	account_rows = frappe.db.get_all(
		"Account",
		filters={"company": company},
		fields=["name", "account_name", "root_type", "lft", "rgt"],
	)
	by_name = {row.name: row for row in account_rows}
	by_account_name = {row.account_name: row for row in account_rows}
	company_abbr = frappe.get_cached_value("Company", company, "abbr")

	accounts = []
	for label in DIVISION_TRANSFER_ACCOUNTS:
		account = by_name.get(label) or by_account_name.get(label)

		if not account and company_abbr and not label.endswith(f" - {company_abbr}"):
			account = by_name.get(f"{label} - {company_abbr}") or by_account_name.get(label)

		if account:
			accounts.append(frappe._dict(account))
		else:
			accounts.append(frappe._dict({"name": label, "label": label, "root_type": None}))

	return accounts




def get_report_cost_centers(filters: frappe._dict, balances: dict[str, dict[str, float]]) -> list[str]:
	if filters.get("cost_center"):
		return sorted(get_cost_centers_with_children(filters.cost_center))

	cost_centers = set()
	for account_balances in balances.values():
		cost_centers.update(cost_center for cost_center, amount in account_balances.items() if flt(amount))
	return sorted(cost_centers)


def get_cost_center_balances(
	filters: frappe._dict, accounts: list[frappe._dict]
) -> dict[str, dict[str, float]]:
	balances = {}
	for account in accounts:
		balances[account.name] = get_account_cost_center_balances(filters, account)
	return balances


def get_account_cost_center_balances(filters: frappe._dict, account: frappe._dict) -> dict[str, float]:
	if not account.name or account.get("lft") is None or account.get("rgt") is None:
		return {}

	conditions = [
		"gle.company = %(company)s",
		"gle.is_cancelled = 0",
		"gle.posting_date <= %(to_date)s",
		"IFNULL(gle.cost_center, '') != ''",
		"acc.lft >= %(lft)s",
		"acc.rgt <= %(rgt)s",
	]
	values = {
		"company": filters.company,
		"to_date": filters.to_date,
		"lft": account.lft,
		"rgt": account.rgt,
	}

	if filters.get("cost_center"):
		cost_centers = get_cost_centers_with_children(filters.cost_center)
		conditions.append("gle.cost_center IN %(cost_centers)s")
		values["cost_centers"] = tuple(cost_centers)

	rows = frappe.db.sql(
		f"""
		SELECT gle.cost_center, SUM(gle.debit - gle.credit) AS amount
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {" AND ".join(conditions)}
		GROUP BY gle.cost_center
		""",
		values,
		as_dict=True,
	)
	return {row.cost_center: flt(row.amount) for row in rows}


def fieldname_for(cost_center: str) -> str:
	return f"cc_{frappe.scrub(cost_center)}"[:120]
