# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
	return get_columns(), get_data(filters or {})


def col(label, fieldname, fieldtype="Float", options=None, width=120):
	column = {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
	if options:
		column["options"] = options
	return column


def get_columns() -> list[dict]:
	return [
		col("Item Type", "item_type", "Data", width=100),
		col("Item Code", "item_code", "Link", "Item", 170),
		col("Warehouse", "warehouse", "Link", "Warehouse", 190),
		col("Definition Qty", "definition_qty"),
		col("Definition Rate", "definition_rate"),
		col("Definition Amount", "definition_amount"),
		col("Process Order Qty", "order_qty"),
		col("Process Order Rate", "order_rate"),
		col("Process Order Amount", "order_amount"),
		col("Batch Order Qty", "batch_qty"),
		col("Batch Order Rate", "batch_rate"),
		col("Batch Order Amount", "batch_amount"),
		col("Stock Entry Qty", "stock_qty"),
		col("Stock Entry Rate", "stock_rate"),
		col("Stock Entry Amount", "stock_amount"),
	]


def get_data(filters: dict) -> list[dict]:
	query = f"""
		SELECT
			item_type,
			item_code,
			warehouse,
			SUM(definition_qty) AS definition_qty,
			IFNULL(SUM(definition_amount) / NULLIF(SUM(definition_qty), 0), 0) AS definition_rate,
			SUM(definition_amount) AS definition_amount,
			SUM(order_qty) AS order_qty,
			IFNULL(SUM(order_amount) / NULLIF(SUM(order_qty), 0), 0) AS order_rate,
			SUM(order_amount) AS order_amount,
			SUM(batch_qty) AS batch_qty,
			IFNULL(SUM(batch_amount) / NULLIF(SUM(batch_qty), 0), 0) AS batch_rate,
			SUM(batch_amount) AS batch_amount,
			SUM(stock_qty) AS stock_qty,
			IFNULL(SUM(stock_amount) / NULLIF(SUM(stock_qty), 0), 0) AS stock_rate,
			SUM(stock_amount) AS stock_amount
		FROM (
			{definition_sql(filters)}
			UNION ALL
			{order_sql(filters)}
			UNION ALL
			{batch_sql(filters)}
			UNION ALL
			{stock_sql(filters)}
		) summary
		GROUP BY item_type, item_code, warehouse
		ORDER BY FIELD(item_type, 'Raw', 'Finish', 'Scrap'), item_code, warehouse
	"""
	return frappe.db.sql(query, get_values(filters), as_dict=True)


def get_values(filters: dict) -> dict:
	return {
		"process_definition": filters.get("process_definition"),
		"process_type": filters.get("process_type"),
		"process_order_id": filters.get("process_order_id"),
		"department": filters.get("department"),
		"project": filters.get("project"),
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
	}


def definition_conditions(filters: dict) -> str:
	conditions = process_definition_conditions(filters)
	order_filters = []

	if filters.get("process_order_id"):
		order_filters.append("p_filter.name = %(process_order_id)s")
	if filters.get("department"):
		order_filters.append("p_filter.department = %(department)s")
	if filters.get("project"):
		order_filters.append("p_filter.project = %(project)s")

	if order_filters:
		conditions.append(
			"""
			EXISTS (
				SELECT 1
				FROM `tabProcess Order s` p_filter
				WHERE p_filter.process_definition = d.name
					AND {order_filter_clause}
			)
			""".format(order_filter_clause=" AND ".join(order_filters))
		)

	return where_clause(conditions)


def order_conditions(filters: dict) -> str:
	conditions = process_definition_conditions(filters)

	if filters.get("process_order_id"):
		conditions.append("p.name = %(process_order_id)s")
	if filters.get("department"):
		conditions.append("p.department = %(department)s")
	if filters.get("project"):
		conditions.append("p.project = %(project)s")

	return where_clause(conditions)


def batch_conditions(filters: dict) -> str:
	conditions = process_definition_conditions(filters)

	if filters.get("process_order_id"):
		conditions.append("p.name = %(process_order_id)s")
	if filters.get("department"):
		conditions.append("b.department = %(department)s")
	if filters.get("project"):
		conditions.append("b.project = %(project)s")

	return where_clause(conditions)


def process_definition_conditions(filters: dict) -> list[str]:
	conditions = []

	if filters.get("process_definition"):
		conditions.append("d.name = %(process_definition)s")
	if filters.get("process_type"):
		conditions.append("d.process_type = %(process_type)s")
	if filters.get("from_date"):
		conditions.append("d.date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("d.date <= %(to_date)s")

	return conditions


def where_clause(conditions: list[str]) -> str:
	return "WHERE " + " AND ".join(conditions) if conditions else ""


def blank_metric_columns() -> str:
	return """
		0 AS definition_qty,
		0 AS definition_amount,
		0 AS order_qty,
		0 AS order_amount,
		0 AS batch_qty,
		0 AS batch_amount,
		0 AS stock_qty,
		0 AS stock_amount
	"""


def definition_sql(filters: dict) -> str:
	where = definition_conditions(filters)
	return f"""
		SELECT item_type, item_code, warehouse,
			SUM(qty) AS definition_qty,
			SUM(amount) AS definition_amount,
			0 AS order_qty,
			0 AS order_amount,
			0 AS batch_qty,
			0 AS batch_amount,
			0 AS stock_qty,
			0 AS stock_amount
		FROM (
			SELECT 'Raw' AS item_type, r.item_code, r.warehouse, r.qty, r.amount
			FROM `tabProcess Definition s` d
			INNER JOIN `tabProcess Definition raw` r ON r.parent = d.name
				AND r.parenttype = 'Process Definition s'
				AND r.parentfield = 'process_definition_raw'
			{where}

			UNION ALL

			SELECT 'Finish' AS item_type, f.item_code, f.warehouse, f.qty, f.amount
			FROM `tabProcess Definition s` d
			INNER JOIN `tabProcess Definition Finish` f ON f.parent = d.name
				AND f.parenttype = 'Process Definition s'
				AND f.parentfield = 'process_definition_finish'
			{where}

			UNION ALL

			SELECT 'Scrap' AS item_type, s.item_code, s.warehouse, s.qty, s.amount
			FROM `tabProcess Definition s` d
			INNER JOIN `tabProcess Definition Scrap` s ON s.parent = d.name
				AND s.parenttype = 'Process Definition s'
				AND s.parentfield = 'process_definition_scrap'
			{where}
		) x
		GROUP BY item_type, item_code, warehouse
	"""


def order_sql(filters: dict) -> str:
	where = order_conditions(filters)
	return f"""
		SELECT item_type, item_code, warehouse,
			0 AS definition_qty,
			0 AS definition_amount,
			SUM(qty) AS order_qty,
			SUM(amount) AS order_amount,
			0 AS batch_qty,
			0 AS batch_amount,
			0 AS stock_qty,
			0 AS stock_amount
		FROM (
			SELECT 'Raw' AS item_type, r.item_code, r.warehouse, r.qty, r.amount
			FROM `tabProcess Definition s` d
			INNER JOIN `tabProcess Order s` p ON p.process_definition = d.name
			INNER JOIN `tabProcess Order raw` r ON r.parent = p.name
				AND r.parenttype = 'Process Order s'
				AND r.parentfield = 'process_definition_raw'
			{where}

			UNION ALL

			SELECT 'Finish' AS item_type, f.item_code, f.warehouse, f.qty, f.amount
			FROM `tabProcess Definition s` d
			INNER JOIN `tabProcess Order s` p ON p.process_definition = d.name
			INNER JOIN `tabProcess Order Finish` f ON f.parent = p.name
				AND f.parenttype = 'Process Order s'
				AND f.parentfield = 'process_definition_finish'
			{where}

			UNION ALL

			SELECT 'Scrap' AS item_type, s.item_code, s.warehouse, s.qty, s.amount
			FROM `tabProcess Definition s` d
			INNER JOIN `tabProcess Order s` p ON p.process_definition = d.name
			INNER JOIN `tabProcess Order Scrap` s ON s.parent = p.name
				AND s.parenttype = 'Process Order s'
				AND s.parentfield = 'process_definition_scrap'
			{where}
		) x
		GROUP BY item_type, item_code, warehouse
	"""


def batch_sql(filters: dict) -> str:
	where = batch_conditions(filters)
	return f"""
		SELECT item_type, item_code, warehouse,
			0 AS definition_qty,
			0 AS definition_amount,
			0 AS order_qty,
			0 AS order_amount,
			SUM(qty) AS batch_qty,
			SUM(amount) AS batch_amount,
			0 AS stock_qty,
			0 AS stock_amount
		FROM (
			SELECT 'Raw' AS item_type, r.item_code, r.warehouse, r.qty, r.amount
			FROM `tabProcess Definition s` d
			INNER JOIN `tabProcess Order s` p ON p.process_definition = d.name
			INNER JOIN `tabBatch Order s` b ON b.process_order = p.name
			INNER JOIN `tabProcess Batch raw` r ON r.parent = b.name
				AND r.parenttype = 'Batch Order s'
				AND r.parentfield = 'process_definition_raw'
			{where}

			UNION ALL

			SELECT 'Finish' AS item_type, f.item_code, f.warehouse, f.qty, f.amount
			FROM `tabProcess Definition s` d
			INNER JOIN `tabProcess Order s` p ON p.process_definition = d.name
			INNER JOIN `tabBatch Order s` b ON b.process_order = p.name
			INNER JOIN `tabProcess Batch Finish` f ON f.parent = b.name
				AND f.parenttype = 'Batch Order s'
				AND f.parentfield = 'process_definition_finish'
			{where}

			UNION ALL

			SELECT 'Scrap' AS item_type, s.item_code, s.warehouse, s.qty, s.amount
			FROM `tabProcess Definition s` d
			INNER JOIN `tabProcess Order s` p ON p.process_definition = d.name
			INNER JOIN `tabBatch Order s` b ON b.process_order = p.name
			INNER JOIN `tabProcess Batch Scrap` s ON s.parent = b.name
				AND s.parenttype = 'Batch Order s'
				AND s.parentfield = 'process_definition_scrap'
			{where}
		) x
		GROUP BY item_type, item_code, warehouse
	"""


def stock_sql(filters: dict) -> str:
	where = batch_conditions(filters)
	return f"""
		SELECT item_type, item_code, warehouse,
			0 AS definition_qty,
			0 AS definition_amount,
			0 AS order_qty,
			0 AS order_amount,
			0 AS batch_qty,
			0 AS batch_amount,
			SUM(qty) AS stock_qty,
			SUM(amount) AS stock_amount
		FROM (
			SELECT
				CASE
					WHEN EXISTS (
						SELECT 1 FROM `tabProcess Batch Scrap` bs
						WHERE bs.parent = b.name AND bs.item_code = sed.item_code
					) THEN 'Scrap'
					WHEN sed.is_scrap_item = 1 THEN 'Scrap'
					WHEN EXISTS (
						SELECT 1 FROM `tabProcess Batch Finish` bf
						WHERE bf.parent = b.name AND bf.item_code = sed.item_code
					) THEN 'Finish'
					WHEN sed.is_finished_item = 1 OR sed.t_warehouse IS NOT NULL THEN 'Finish'
					ELSE 'Raw'
				END AS item_type,
				sed.item_code,
				COALESCE(sed.t_warehouse, sed.s_warehouse) AS warehouse,
				sed.qty,
				sed.amount
			FROM `tabProcess Definition s` d
			INNER JOIN `tabProcess Order s` p ON p.process_definition = d.name
			INNER JOIN `tabBatch Order s` b ON b.process_order = p.name
			INNER JOIN `tabStock Entry` se ON se.custom_batch_order_id = b.name
			INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
			{where}
		) x
		GROUP BY item_type, item_code, warehouse
	"""
