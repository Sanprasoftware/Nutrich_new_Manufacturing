# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.data import getdate


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	opening = get_opening(filters)
	transfers = get_transfers(filters)
	cost_centers = get_cost_centers(opening, transfers)
	columns = get_columns(filters, cost_centers)
	data = get_data(opening, transfers, cost_centers, filters.cost_center)

	return columns, data


def validate_filters(filters: frappe._dict):
	if not filters.company:
		frappe.throw(_("Company is required"))
	if not filters.from_date:
		frappe.throw(_("From Date is required"))
	if not filters.to_date:
		frappe.throw(_("To Date is required"))
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date"))


def col(label, fieldname, fieldtype="Currency", options=None, width=130):
	column = {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
	if options:
		column["options"] = options
	return column


def get_columns(filters: frappe._dict, cost_centers: list[str]) -> list[dict]:
	opening_label = filters.fiscal_year or _("Opening")
	columns = [
		col("Account", "cost_center", "Link", "Cost Center", 220),
		col(opening_label, "opening", width=140),
	]

	for cost_center in cost_centers:
		columns.append(col(cost_center, fieldname_for(cost_center), width=150))

	columns.extend(
		[
			col("All Total", "all_total", width=140),
			col("Diff.", "diff", width=140),
		]
	)
	return columns


def get_data(
	opening: dict[str, float],
	transfers: dict[str, dict[str, float]],
	cost_centers: list[str],
	filter_cost_center: str | None = None,
) -> list[dict]:
	row_cost_centers = sorted(set(opening) | set(transfers))
	if filter_cost_center:
		row_cost_centers = [cost_center for cost_center in row_cost_centers if cost_center == filter_cost_center]

	data = []

	for row_cost_center in row_cost_centers:
		row = {
			"cost_center": row_cost_center,
			"opening": flt(opening.get(row_cost_center)),
		}

		all_total = 0
		for column_cost_center in cost_centers:
			amount = flt(transfers.get(row_cost_center, {}).get(column_cost_center))
			row[fieldname_for(column_cost_center)] = amount
			all_total += amount

		row["all_total"] = all_total
		row["diff"] = row["opening"] + all_total
		data.append(row)

	return data


def get_opening(filters: frappe._dict) -> dict[str, float]:
	conditions, values = get_conditions(filters, before_from_date=True)
	rows = frappe.db.sql(
		f"""
		SELECT cost_center, SUM(debit - credit) AS amount
		FROM `tabGL Entry`
		WHERE {conditions}
		GROUP BY cost_center
		HAVING ABS(amount) > 0.000001
		""",
		values,
		as_dict=True,
	)
	return {row.cost_center: flt(row.amount) for row in rows if row.cost_center}


def get_transfers(filters: frappe._dict) -> dict[str, dict[str, float]]:
	conditions, values = get_conditions(filters)
	rows = frappe.db.sql(
		f"""
		SELECT voucher_type, voucher_no, cost_center, SUM(debit - credit) AS amount
		FROM `tabGL Entry`
		WHERE {conditions}
		GROUP BY voucher_type, voucher_no, cost_center
		HAVING ABS(amount) > 0.000001
		ORDER BY voucher_type, voucher_no, cost_center
		""",
		values,
		as_dict=True,
	)

	groups = defaultdict(list)
	for row in rows:
		if row.cost_center:
			groups[(row.voucher_type, row.voucher_no)].append(row)

	transfers = defaultdict(lambda: defaultdict(float))
	for group_rows in groups.values():
		apply_transfer_group(group_rows, transfers)

	return transfers


def apply_transfer_group(rows: list[dict], transfers: dict[str, dict[str, float]]):
	debits = [row for row in rows if flt(row.amount) > 0]
	credits = [row for row in rows if flt(row.amount) < 0]

	if not debits or not credits:
		return

	total_debit = sum(flt(row.amount) for row in debits)
	total_credit = sum(abs(flt(row.amount)) for row in credits)
	transfer_amount = min(total_debit, total_credit)

	if not transfer_amount:
		return

	for debit_row in debits:
		debit_share = flt(debit_row.amount) / total_debit
		for credit_row in credits:
			credit_share = abs(flt(credit_row.amount)) / total_credit
			amount = transfer_amount * debit_share * credit_share
			if debit_row.cost_center == credit_row.cost_center:
				continue

			transfers[debit_row.cost_center][credit_row.cost_center] += amount
			transfers[credit_row.cost_center][debit_row.cost_center] -= amount


def get_conditions(filters: frappe._dict, before_from_date: bool = False) -> tuple[str, dict]:
	conditions = [
		"company = %(company)s",
		"is_cancelled = 0",
		"cost_center IS NOT NULL",
		"cost_center != ''",
	]
	values = {
		"company": filters.company,
		"from_date": filters.from_date,
		"to_date": filters.to_date,
		"account": filters.account,
	}

	if before_from_date:
		conditions.append("posting_date < %(from_date)s")
	else:
		conditions.append("posting_date BETWEEN %(from_date)s AND %(to_date)s")

	if filters.account:
		conditions.append("account = %(account)s")

	return " AND ".join(conditions), values 


def get_cost_centers(opening: dict[str, float], transfers: dict[str, dict[str, float]]) -> list[str]:
	cost_centers = set(opening)
	for row_cost_center, row_transfers in transfers.items():
		cost_centers.add(row_cost_center)
		cost_centers.update(row_transfers)
	return sorted(cost_centers)


def fieldname_for(cost_center: str) -> str:
	return f"cc_{frappe.scrub(cost_center)}"[:120]
