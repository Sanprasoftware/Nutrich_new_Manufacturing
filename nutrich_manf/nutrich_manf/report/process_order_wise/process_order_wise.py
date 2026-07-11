# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	return get_columns(), get_data(filters)


def validate_filters(filters: frappe._dict):
	if filters.get("from_date") and filters.get("to_date"):
		if getdate(filters.from_date) > getdate(filters.to_date):
			frappe.throw(_("From Date cannot be after To Date"))


def col(label, fieldname, fieldtype="Float", options=None, width=130, hidden=0):
	column = {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
	if options:
		column["options"] = options
	if hidden:
		column["hidden"] = 1
	return column


def get_columns() -> list[dict]:
	return [
		col("Process Order", "process_order", "Link", "Process Order s", 190),
		col("Warehouse", "warehouse", "Link", "Warehouse", 180),
		col("Item Code", "item_code", "Link", "Item", 150),
		col("Item Name", "item_name", "Data", width=220),
		col("Stock In Qty", "stock_in_qty"),
		col("Rate (In Qty)", "stock_in_rate", "Currency"),
		col("Amount (In Qty)", "stock_in_amount", "Currency"),
		col("Stock Out Qty", "stock_out_qty"),
		col("Rate (Out Qty)", "stock_out_rate", "Currency"),
		col("Amount (Out Qty)", "stock_out_amount", "Currency"),
		col("Yield %", "yield_percent", "Percent", width=110),
		col("Process Cost", "process_cost", "Currency"),
		col("Per Kg Process Cost", "per_kg_process_cost", "Currency", width=170),
		col("Row Color", "row_color", "Data", hidden=1),
	]


def get_data(filters: frappe._dict) -> list[dict]:
	conditions, values = get_conditions(filters)
	rows = frappe.db.sql(
		f"""
		SELECT
			b.process_order,
			CASE
				WHEN IFNULL(sed.s_warehouse, '') != '' THEN sed.s_warehouse
				ELSE sed.t_warehouse
			END AS warehouse,
			sed.item_code,
			COALESCE(sed.item_name, i.item_name) AS item_name,
			SUM(CASE WHEN IFNULL(sed.s_warehouse, '') = '' AND IFNULL(sed.t_warehouse, '') != '' THEN sed.qty ELSE 0 END) AS stock_in_qty,
			SUM(CASE WHEN IFNULL(sed.s_warehouse, '') = '' AND IFNULL(sed.t_warehouse, '') != '' THEN sed.amount ELSE 0 END) AS stock_in_amount,
			SUM(CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN sed.qty ELSE 0 END) AS stock_out_qty,
			SUM(CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN sed.amount ELSE 0 END) AS stock_out_amount,
			process_totals.total_stock_in_qty,
			process_totals.total_stock_in_amount,
			process_totals.total_stock_out_qty,
			process_totals.total_stock_out_amount,
			CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN 'raw' ELSE 'finish' END AS row_color,
			CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN 1 ELSE 2 END AS sort_order
		FROM `tabStock Entry` se
		INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
		INNER JOIN `tabBatch Order s` b ON b.name = se.custom_batch_order_id
		LEFT JOIN `tabItem` i ON i.name = sed.item_code
		LEFT JOIN (
			SELECT
				b_inner.process_order,
				SUM(CASE WHEN IFNULL(sed_inner.s_warehouse, '') = '' AND IFNULL(sed_inner.t_warehouse, '') != '' THEN sed_inner.qty ELSE 0 END) AS total_stock_in_qty,
				SUM(CASE WHEN IFNULL(sed_inner.s_warehouse, '') = '' AND IFNULL(sed_inner.t_warehouse, '') != '' THEN sed_inner.amount ELSE 0 END) AS total_stock_in_amount,
				SUM(CASE WHEN IFNULL(sed_inner.s_warehouse, '') != '' THEN sed_inner.qty ELSE 0 END) AS total_stock_out_qty,
				SUM(CASE WHEN IFNULL(sed_inner.s_warehouse, '') != '' THEN sed_inner.amount ELSE 0 END) AS total_stock_out_amount
			FROM `tabStock Entry` se_inner
			INNER JOIN `tabStock Entry Detail` sed_inner ON sed_inner.parent = se_inner.name
			INNER JOIN `tabBatch Order s` b_inner ON b_inner.name = se_inner.custom_batch_order_id
			WHERE {conditions.replace('se.', 'se_inner.').replace('sed.', 'sed_inner.').replace('b.', 'b_inner.')}
			GROUP BY b_inner.process_order
		) process_totals ON process_totals.process_order = b.process_order
		WHERE {conditions}
		GROUP BY
			b.process_order,
			CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN sed.s_warehouse ELSE sed.t_warehouse END,
			sed.item_code,
			COALESCE(sed.item_name, i.item_name),
			CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN 'raw' ELSE 'finish' END,
			process_totals.total_stock_in_qty,
			process_totals.total_stock_in_amount,
			process_totals.total_stock_out_qty,
			process_totals.total_stock_out_amount
		HAVING ABS(stock_in_qty) > 0.000001
			OR ABS(stock_in_amount) > 0.000001
			OR ABS(stock_out_qty) > 0.000001
			OR ABS(stock_out_amount) > 0.000001
		ORDER BY b.process_order, sort_order, sed.item_code, warehouse
		""",
		values,
		as_dict=True,
	)

	previous_process_order = None
	for row in rows:
		process_order = row.process_order
		row.stock_in_qty = flt(row.stock_in_qty)
		row.stock_in_amount = flt(row.stock_in_amount)
		row.stock_in_rate = flt(row.stock_in_amount / row.stock_in_qty) if row.stock_in_qty else 0
		row.stock_out_qty = flt(row.stock_out_qty)
		row.stock_out_amount = flt(row.stock_out_amount)
		row.stock_out_rate = flt(row.stock_out_amount / row.stock_out_qty) if row.stock_out_qty else 0

		total_stock_in_qty = flt(row.pop("total_stock_in_qty", 0))
		total_stock_in_amount = flt(row.pop("total_stock_in_amount", 0))
		total_stock_out_qty = flt(row.pop("total_stock_out_qty", 0))
		total_stock_out_amount = flt(row.pop("total_stock_out_amount", 0))
		row.pop("sort_order", None)

		is_finish_row = row.row_color == "finish"
		is_first_process_order_row = process_order != previous_process_order
		process_cost = flt(total_stock_in_amount - total_stock_out_amount)

		row.yield_percent = flt((row.stock_in_qty / total_stock_out_qty) * 100) if is_finish_row and total_stock_out_qty else None
		row.process_cost = process_cost if is_first_process_order_row else None
		row.per_kg_process_cost = flt(process_cost / total_stock_in_qty) if is_first_process_order_row and total_stock_in_qty else None

		if is_first_process_order_row:
			previous_process_order = process_order
		else:
			row.process_order = None

	return rows


def get_conditions(filters: frappe._dict) -> tuple[str, dict]:
	conditions = [
		"se.docstatus = 1",
		"sed.docstatus = 1",
		"se.stock_entry_type = 'Manufacture'",
		"IFNULL(se.custom_batch_order_id, '') != ''",
		"IFNULL(b.process_order, '') != ''",
	]
	values = {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
		"process_order": filters.get("process_order"),
		"process_type": filters.get("process_type"),
	}

	if filters.get("from_date"):
		conditions.append("se.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("se.posting_date <= %(to_date)s")
	if filters.get("process_order"):
		conditions.append("b.process_order = %(process_order)s")
	if filters.get("process_type"):
		conditions.append("b.process_type = %(process_type)s")

	return " AND ".join(conditions), values
