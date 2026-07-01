# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	data = get_data(filters)
	set_process_yield(data)
	return get_columns(), data


def validate_filters(filters: frappe._dict):
	if filters.get("from_date") and filters.get("to_date"):
		if getdate(filters.from_date) > getdate(filters.to_date):
			frappe.throw(_("From Date cannot be after To Date"))


def col(label, fieldname, fieldtype="Float", options=None, width=130):
	column = {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
	if options:
		column["options"] = options
	return column


def get_columns() -> list[dict]:
	return [
		col("Process Type", "process_type", "Link", "Process Type s", 180),
		col("Stock Item", "stock_item", "Link", "Item", 150),
		col("Stock Item Name", "stock_item_name", "Data", width=220),
		col("Stock In Qty", "stock_in_qty"),
		col("Stock in Rate", "stock_in_rate", "Currency"),
		col("Stock in Amt", "stock_in_amount", "Currency"),
		col("Stock Out Qty", "stock_out_qty"),
		col("Stock Yield", "stock_yield", "Percent"),
		col("Stock Out Rate", "stock_out_rate", "Currency"),
		col("Diff Amount Stock In and Out", "diff_amount", "Currency", width=190),
		col("Process. Cost /Kg on In Qty", "process_cost_per_kg_on_in_qty", "Currency", width=190),
	]


def get_data(filters: frappe._dict) -> list[dict]:
	conditions, values = get_conditions(filters)
	query = f"""
		SELECT
			COALESCE(b.process_type, p.process_type) AS process_type,
			sed.item_code AS stock_item,
			COALESCE(sed.item_name, i.item_name) AS stock_item_name,
			SUM(CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN sed.qty ELSE 0 END) AS stock_in_qty,
			SUM(CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN sed.amount ELSE 0 END) AS stock_in_amount,
			SUM(CASE WHEN IFNULL(sed.t_warehouse, '') != '' THEN sed.qty ELSE 0 END) AS stock_out_qty,
			SUM(CASE WHEN IFNULL(sed.t_warehouse, '') != '' THEN sed.amount ELSE 0 END) AS stock_out_amount,
			SUM(
				CASE
					WHEN IFNULL(sed.s_warehouse, '') != '' AND entry_totals.stock_in_qty > 0
					THEN IFNULL(se.value_difference, 0) * sed.qty / entry_totals.stock_in_qty
					ELSE 0
				END
			) AS allocated_process_cost
		FROM `tabStock Entry` se
		INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
		LEFT JOIN `tabBatch Order s` b ON b.name = se.custom_batch_order_id
		LEFT JOIN `tabProcess Order s` p ON p.name = b.process_order
		LEFT JOIN `tabItem` i ON i.name = sed.item_code
		LEFT JOIN (
			SELECT parent, SUM(qty) AS stock_in_qty
			FROM `tabStock Entry Detail`
			WHERE IFNULL(s_warehouse, '') != ''
			GROUP BY parent
		) entry_totals ON entry_totals.parent = se.name
		WHERE {conditions}
		GROUP BY COALESCE(b.process_type, p.process_type), sed.item_code, COALESCE(sed.item_name, i.item_name)
		HAVING ABS(stock_in_qty) > 0.000001
			OR ABS(stock_in_amount) > 0.000001
			OR ABS(stock_out_qty) > 0.000001
			OR ABS(stock_out_amount) > 0.000001
		ORDER BY process_type, stock_item
	"""
	rows = frappe.db.sql(query, values, as_dict=True)

	for row in rows:
		row.stock_in_qty = flt(row.stock_in_qty)
		row.stock_in_amount = flt(row.stock_in_amount)
		row.stock_out_qty = flt(row.stock_out_qty)
		row.stock_out_amount = flt(row.stock_out_amount)
		row.stock_in_rate = flt(row.stock_in_amount / row.stock_in_qty) if row.stock_in_qty else 0
		row.stock_out_rate = flt(row.stock_out_amount / row.stock_out_qty) if row.stock_out_qty else 0
		row.diff_amount = flt(row.stock_out_amount - row.stock_in_amount)
		row.process_cost_per_kg_on_in_qty = (
			flt(row.allocated_process_cost / row.stock_in_qty) if row.stock_in_qty else 0
		)

	return rows


def get_conditions(filters: frappe._dict) -> tuple[str, dict]:
	conditions = [
		"se.docstatus = 1",
		"sed.docstatus = 1",
		"se.stock_entry_type = 'Manufacture'",
	]
	values = {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
		"process_type": filters.get("process_type"),
		"process_order_id": filters.get("process_order_id"),
		"batch_order_id": filters.get("batch_order_id"),
		"stock_entry": filters.get("stock_entry"),
		"project": filters.get("project"),
		"item_code": filters.get("item_code"),
	}

	if filters.get("from_date"):
		conditions.append("se.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("se.posting_date <= %(to_date)s")
	if filters.get("process_type"):
		conditions.append("COALESCE(b.process_type, p.process_type) = %(process_type)s")
	if filters.get("process_order_id"):
		conditions.append("b.process_order = %(process_order_id)s")
	if filters.get("batch_order_id"):
		conditions.append("se.custom_batch_order_id = %(batch_order_id)s")
	if filters.get("stock_entry"):
		conditions.append("se.name = %(stock_entry)s")
	if filters.get("project"):
		conditions.append("COALESCE(se.project, b.project, p.project) = %(project)s")
	if filters.get("item_code"):
		conditions.append("sed.item_code = %(item_code)s")

	return " AND ".join(conditions), values


def set_process_yield(data: list[dict]):
	process_in_qty = {}
	for row in data:
		process_in_qty[row.process_type] = process_in_qty.get(row.process_type, 0) + flt(row.stock_in_qty)

	for row in data:
		total_in_qty = process_in_qty.get(row.process_type)
		row.stock_yield = flt((row.stock_out_qty / total_in_qty) * 100) if total_in_qty else 0
