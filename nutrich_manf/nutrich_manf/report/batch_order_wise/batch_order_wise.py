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
		col("Batch Order ID", "batch_order_id", "Link", "Batch Order s", 180),
		col("Process Order ID", "process_order_id", "Link", "Process Order s", 190),
		col("Stock Entry ID", "stock_entry_id", "Link", "Stock Entry", 180),
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
			se.custom_batch_order_id AS batch_order_id,
			b.process_order AS process_order_id,
			se.name AS stock_entry_id,
			CASE
				WHEN IFNULL(sed.s_warehouse, '') != '' THEN sed.s_warehouse
				ELSE sed.t_warehouse
			END AS warehouse,
			sed.item_code,
			COALESCE(sed.item_name, i.item_name) AS item_name,
			CASE WHEN IFNULL(sed.s_warehouse, '') = '' AND IFNULL(sed.t_warehouse, '') != '' THEN sed.qty ELSE 0 END AS stock_in_qty,
			CASE WHEN IFNULL(sed.s_warehouse, '') = '' AND IFNULL(sed.t_warehouse, '') != '' THEN sed.basic_rate ELSE 0 END AS stock_in_rate,
			CASE WHEN IFNULL(sed.s_warehouse, '') = '' AND IFNULL(sed.t_warehouse, '') != '' THEN sed.amount ELSE 0 END AS stock_in_amount,
			CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN sed.qty ELSE 0 END AS stock_out_qty,
			CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN sed.basic_rate ELSE 0 END AS stock_out_rate,
			CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN sed.amount ELSE 0 END AS stock_out_amount,
			entry_totals.total_stock_in_qty,
			entry_totals.total_stock_in_amount,
			entry_totals.total_stock_out_qty,
			entry_totals.total_stock_out_amount,
			CASE WHEN IFNULL(sed.s_warehouse, '') != '' THEN 'raw' ELSE 'finish' END AS row_color,
			sed.idx AS child_idx
		FROM `tabStock Entry` se
		INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
		INNER JOIN `tabBatch Order s` b ON b.name = se.custom_batch_order_id
		LEFT JOIN `tabItem` i ON i.name = sed.item_code
		LEFT JOIN (
			SELECT
				parent,
				SUM(CASE WHEN IFNULL(s_warehouse, '') = '' AND IFNULL(t_warehouse, '') != '' THEN qty ELSE 0 END) AS total_stock_in_qty,
				SUM(CASE WHEN IFNULL(s_warehouse, '') = '' AND IFNULL(t_warehouse, '') != '' THEN amount ELSE 0 END) AS total_stock_in_amount,
				SUM(CASE WHEN IFNULL(s_warehouse, '') != '' THEN qty ELSE 0 END) AS total_stock_out_qty,
				SUM(CASE WHEN IFNULL(s_warehouse, '') != '' THEN amount ELSE 0 END) AS total_stock_out_amount
			FROM `tabStock Entry Detail`
			WHERE docstatus = 1
			GROUP BY parent
		) entry_totals ON entry_totals.parent = se.name
		WHERE {conditions}
		ORDER BY se.custom_batch_order_id, b.process_order, se.name, sed.idx
		""",
		values,
		as_dict=True,
	)

	data = []
	previous_batch_order_id = None
	previous_stock_entry_id = None

	for row in rows:
		batch_order_id = row.batch_order_id
		stock_entry_id = row.stock_entry_id

		if previous_batch_order_id is not None and batch_order_id != previous_batch_order_id:
			data.append({})

		row.stock_in_qty = flt(row.stock_in_qty)
		row.stock_in_rate = flt(row.stock_in_rate)
		row.stock_in_amount = flt(row.stock_in_amount)
		row.stock_out_qty = flt(row.stock_out_qty)
		row.stock_out_rate = flt(row.stock_out_rate)
		row.stock_out_amount = flt(row.stock_out_amount)

		total_stock_in_qty = flt(row.pop("total_stock_in_qty", 0))
		total_stock_in_amount = flt(row.pop("total_stock_in_amount", 0))
		total_stock_out_qty = flt(row.pop("total_stock_out_qty", 0))
		total_stock_out_amount = flt(row.pop("total_stock_out_amount", 0))

		is_finish_row = row.row_color == "finish"
		is_first_stock_entry_row = stock_entry_id != previous_stock_entry_id
		process_cost = flt(total_stock_in_amount - total_stock_out_amount)

		row.yield_percent = flt((row.stock_in_qty / total_stock_out_qty) * 100) if is_finish_row and total_stock_out_qty else None
		row.process_cost = process_cost if is_first_stock_entry_row else None
		row.per_kg_process_cost = flt(process_cost / total_stock_in_qty) if is_first_stock_entry_row and total_stock_in_qty else None

		data.append(row)
		previous_batch_order_id = batch_order_id
		previous_stock_entry_id = stock_entry_id

	return data


def get_conditions(filters: frappe._dict) -> tuple[str, dict]:
	conditions = [
		"se.docstatus = 1",
		"sed.docstatus = 1",
		"se.stock_entry_type = 'Manufacture'",
		"IFNULL(se.custom_batch_order_id, '') != ''",
	]
	values = {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
		"batch_order_id": filters.get("batch_order_id"),
		"process_type": filters.get("process_type"),
		"process_order_id": filters.get("process_order_id"),
		"stock_entry": filters.get("stock_entry"),
		"warehouse": filters.get("warehouse"),
		"item_code": filters.get("item_code"),
	}

	if filters.get("from_date"):
		conditions.append("se.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("se.posting_date <= %(to_date)s")
	if filters.get("batch_order_id"):
		conditions.append("se.custom_batch_order_id = %(batch_order_id)s")
	if filters.get("process_type"):
		conditions.append("b.process_type = %(process_type)s")
	if filters.get("process_order_id"):
		conditions.append("b.process_order = %(process_order_id)s")
	if filters.get("stock_entry"):
		conditions.append("se.name = %(stock_entry)s")
	if filters.get("warehouse"):
		conditions.append("(sed.s_warehouse = %(warehouse)s OR sed.t_warehouse = %(warehouse)s)")
	if filters.get("item_code"):
		conditions.append("sed.item_code = %(item_code)s")

	return " AND ".join(conditions), values
