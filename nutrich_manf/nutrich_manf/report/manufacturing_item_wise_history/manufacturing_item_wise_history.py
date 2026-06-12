# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
	columns = get_columns()
	data = get_data(filters or {})
	return columns, data


def col(label, fieldname, fieldtype="Data", options=None, width=120, hidden=0):
	column = {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
	if options:
		column["options"] = options
	if hidden:
		column["hidden"] = 1
	return column


def get_columns() -> list[dict]:
	return [
		col("Process Definition", "process_definition", "Link", "Process Definition s", 200),
		col("Definition Date", "definition_date", "Date", width=110),
		col("Definition Process Type", "definition_process_type", "Link", "Process Type s", 170),
		col("Definition Item Type", "definition_item_type", width=130),
		col("Definition Item Code", "definition_item_code", "Link", "Item", 170),
		col("Definition Qty", "definition_qty", "Float", width=110),
		col("Definition Rate", "definition_rate", "Float", width=110),
		col("Definition Amount", "definition_amount", "Float", width=130),
		col("Definition Warehouse", "definition_warehouse", "Link", "Warehouse", 190),
		col("Process Order Count", "process_order_count", "Int", width=150),
		col("Process Order ID", "process_order_id", "Link", "Process Order s", 190),
		col("Order Date", "order_date", "Date", width=110),
		col("Order Process Type", "order_process_type", "Link", "Process Type s", 160),
		col("Order Department", "order_department", "Link", "Manufacturing Department s", 150),
		col("Order Project", "order_project", "Link", "Project", 150),
		col("Process Order Qty", "process_order_qty", "Float", width=140),
		col("Order Item Type", "order_item_type", width=120),
		col("Order Item Code", "order_item_code", "Link", "Item", 170),
		col("Order Qty", "order_qty", "Float", width=100),
		col("Order Rate", "order_rate", "Float", width=100),
		col("Order Amount", "order_amount", "Float", width=120),
		col("Order Warehouse", "order_warehouse", "Link", "Warehouse", 190),
		col("Batch Order Count", "batch_order_count", "Int", width=140),
		col("Batch Order ID", "batch_order_id", "Link", "Batch Order s", 180),
		col("Batch Process Type", "batch_process_type", "Link", "Process Type s", 160),
		col("Batch Date", "batch_date", "Date", width=110),
		col("Batch Time", "batch_time", "Time", width=110),
		col("Batch Status", "batch_status", width=120),
		col("Batch Department", "batch_department", "Link", "Manufacturing Department s", 150),
		col("Batch Project", "batch_project", "Link", "Project", 150),
		col("Batch Cost Center", "batch_cost_center", "Link", "Cost Center", 170),
		col("Batch Item Type", "batch_item_type", width=120),
		col("Batch Item Code", "batch_item_code", "Link", "Item", 170),
		col("Batch Qty", "batch_qty", "Float", width=100),
		col("Batch Rate", "batch_rate", "Float", width=100),
		col("Batch Amount", "batch_amount", "Float", width=120),
		col("Batch Warehouse", "batch_warehouse", "Link", "Warehouse", 190),
		col("Stock Entry Count", "stock_entry_count", "Int", width=140),
		col("Stock Entry ID", "stock_entry_id", "Link", "Stock Entry", 180),
		col("Stock Posting Date", "stock_posting_date", "Date", width=120),
		col("Stock Posting Time", "stock_posting_time", "Time", width=120),
		col("Stock Purpose", "stock_purpose", width=130),
		col("Stock Entry Type", "stock_entry_type", "Link", "Stock Entry Type", 150),
		col("Stock Status", "stock_status", width=110),
		col("Stock Item Type", "stock_item_type", width=120),
		col("Stock Item Code", "stock_item_code", "Link", "Item", 170),
		col("Stock Qty", "stock_qty", "Float", width=100),
		col("Stock Rate", "stock_rate", "Float", width=100),
		col("Stock Amount", "stock_amount", "Float", width=120),
		col("Source Warehouse", "stock_source_warehouse", "Link", "Warehouse", 170),
		col("Target Warehouse", "stock_target_warehouse", "Link", "Warehouse", 170),
		col("Definition Row Color", "definition_row_color", hidden=1),
		col("Order Row Color", "order_row_color", hidden=1),
		col("Batch Row Color", "batch_row_color", hidden=1),
		col("Stock Row Color", "stock_row_color", hidden=1),
	]


def get_data(filters: dict) -> list[dict]:
	data = []

	for definition in get_process_definitions(filters):
		definition_rows = get_definition_rows(definition.name)
		order_rows = get_order_rows(definition.name, filters)
		process_order_ids = [row.process_order_id for row in order_rows if row.process_order_id]
		batch_rows = get_batch_rows(process_order_ids, filters)
		batch_order_ids = [row.batch_order_id for row in batch_rows if row.batch_order_id]
		stock_rows = get_stock_entry_rows(batch_order_ids)

		process_order_count = len(set(process_order_ids))
		batch_order_count = len(set(batch_order_ids))
		stock_entry_count = len({row.stock_entry_id for row in stock_rows if row.stock_entry_id})
		row_count = max(len(definition_rows), len(order_rows), len(batch_rows), len(stock_rows), 1)

		for index in range(row_count):
			row = {}
			if index == 0:
				row.update(
					{
						"process_definition": definition.name,
						"definition_date": definition.date,
						"definition_process_type": definition.process_type,
						"process_order_count": process_order_count,
						"batch_order_count": batch_order_count,
						"stock_entry_count": stock_entry_count,
					}
				)

			if index < len(definition_rows):
				apply_item_row(row, definition_rows[index], "definition")
			if index < len(order_rows):
				apply_order_row(row, order_rows[index])
			if index < len(batch_rows):
				apply_batch_row(row, batch_rows[index])
			if index < len(stock_rows):
				apply_stock_row(row, stock_rows[index])

			data.append(row)

	return blank_repeated_headers(data)


def apply_item_row(target: dict, source: dict, prefix: str):
	target.update(
		{
			f"{prefix}_item_type": source.item_type,
			f"{prefix}_item_code": source.item_code,
			f"{prefix}_qty": source.qty,
			f"{prefix}_rate": source.rate,
			f"{prefix}_amount": source.amount,
			f"{prefix}_warehouse": source.warehouse,
			f"{prefix}_row_color": source.row_color,
		}
	)


def apply_order_row(target: dict, source: dict):
	target.update(
		{
			"process_order_id": source.process_order_id,
			"order_date": source.order_date,
			"order_process_type": source.order_process_type,
			"order_department": source.department,
			"order_project": source.project,
			"process_order_qty": source.process_order_qty,
			"order_item_type": source.item_type,
			"order_item_code": source.item_code,
			"order_qty": source.qty,
			"order_rate": source.rate,
			"order_amount": source.amount,
			"order_warehouse": source.warehouse,
			"order_row_color": source.row_color,
		}
	)


def apply_batch_row(target: dict, source: dict):
	target.update(
		{
			"batch_order_id": source.batch_order_id,
			"batch_process_type": source.batch_process_type,
			"batch_date": source.batch_date,
			"batch_time": source.batch_time,
			"batch_status": source.batch_status,
			"batch_department": source.batch_department,
			"batch_project": source.batch_project,
			"batch_cost_center": source.batch_cost_center,
			"batch_item_type": source.item_type,
			"batch_item_code": source.item_code,
			"batch_qty": source.qty,
			"batch_rate": source.rate,
			"batch_amount": source.amount,
			"batch_warehouse": source.warehouse,
			"batch_row_color": source.row_color,
		}
	)


def apply_stock_row(target: dict, source: dict):
	target.update(
		{
			"stock_entry_id": source.stock_entry_id,
			"stock_posting_date": source.stock_posting_date,
			"stock_posting_time": source.stock_posting_time,
			"stock_purpose": source.stock_purpose,
			"stock_entry_type": source.stock_entry_type,
			"stock_status": source.stock_status,
			"stock_item_type": source.item_type,
			"stock_item_code": source.item_code,
			"stock_qty": source.qty,
			"stock_rate": source.rate,
			"stock_amount": source.amount,
			"stock_source_warehouse": source.s_warehouse,
			"stock_target_warehouse": source.t_warehouse,
			"stock_row_color": source.row_color,
		}
	)


def get_process_definitions(filters: dict) -> list[dict]:
	conditions = []
	values = []

	if filters.get("process_definition"):
		conditions.append("name = %s")
		values.append(filters.get("process_definition"))
	if filters.get("process_type"):
		conditions.append("process_type = %s")
		values.append(filters.get("process_type"))
	if filters.get("from_date"):
		conditions.append("date >= %s")
		values.append(filters.get("from_date"))
	if filters.get("to_date"):
		conditions.append("date <= %s")
		values.append(filters.get("to_date"))

	where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
	return frappe.db.sql(
		f"""
		SELECT name, date, process_type
		FROM `tabProcess Definition s`
		{where_clause}
		ORDER BY date DESC, name
		""",
		values,
		as_dict=True,
	)


def get_definition_rows(process_definition: str) -> list[dict]:
	return get_child_item_rows(
		"Process Definition s",
		process_definition,
		"Process Definition raw",
		"Process Definition Finish",
		"Process Definition Scrap",
	)


def get_child_item_rows(parenttype: str, parent: str, raw_doctype: str, finish_doctype: str, scrap_doctype: str) -> list[dict]:
	return frappe.db.sql(
		f"""
		SELECT 'Raw' AS item_type, item_code, qty, rate, amount, warehouse, 'raw' AS row_color, 1 AS sort_order, idx
		FROM `tab{raw_doctype}`
		WHERE parent = %s AND parenttype = %s AND parentfield = 'process_definition_raw'

		UNION ALL

		SELECT 'Finish' AS item_type, item_code, qty, rate, amount, warehouse, 'finish' AS row_color, 2 AS sort_order, idx
		FROM `tab{finish_doctype}`
		WHERE parent = %s AND parenttype = %s AND parentfield = 'process_definition_finish'

		UNION ALL

		SELECT 'Scrap' AS item_type, item_code, qty, rate, amount, warehouse, 'scrap' AS row_color, 3 AS sort_order, idx
		FROM `tab{scrap_doctype}`
		WHERE parent = %s AND parenttype = %s AND parentfield = 'process_definition_scrap'

		ORDER BY sort_order, idx
		""",
		(parent, parenttype, parent, parenttype, parent, parenttype),
		as_dict=True,
	)


def get_order_rows(process_definition: str, filters: dict) -> list[dict]:
	conditions = ["p.process_definition = %s"]
	values = [process_definition]

	if filters.get("process_order_id"):
		conditions.append("p.name = %s")
		values.append(filters.get("process_order_id"))
	if filters.get("department"):
		conditions.append("p.department = %s")
		values.append(filters.get("department"))
	if filters.get("project"):
		conditions.append("p.project = %s")
		values.append(filters.get("project"))

	where_clause = "WHERE " + " AND ".join(conditions)
	return frappe.db.sql(
		f"""
		SELECT p.name AS process_order_id, p.date AS order_date, p.process_type AS order_process_type,
			p.department, p.project, p.process_order_qty, 'Raw' AS item_type, r.item_code, r.qty,
			r.rate, r.amount, r.warehouse, 'raw' AS row_color, 1 AS sort_order, r.idx AS child_idx
		FROM `tabProcess Order s` p
		INNER JOIN `tabProcess Order raw` r ON r.parent = p.name AND r.parenttype = 'Process Order s'
			AND r.parentfield = 'process_definition_raw'
		{where_clause}

		UNION ALL

		SELECT p.name AS process_order_id, p.date AS order_date, p.process_type AS order_process_type,
			p.department, p.project, p.process_order_qty, 'Finish' AS item_type, f.item_code, f.qty,
			f.rate, f.amount, f.warehouse, 'finish' AS row_color, 2 AS sort_order, f.idx AS child_idx
		FROM `tabProcess Order s` p
		INNER JOIN `tabProcess Order Finish` f ON f.parent = p.name AND f.parenttype = 'Process Order s'
			AND f.parentfield = 'process_definition_finish'
		{where_clause}

		UNION ALL

		SELECT p.name AS process_order_id, p.date AS order_date, p.process_type AS order_process_type,
			p.department, p.project, p.process_order_qty, 'Scrap' AS item_type, s.item_code, s.qty,
			s.rate, s.amount, s.warehouse, 'scrap' AS row_color, 3 AS sort_order, s.idx AS child_idx
		FROM `tabProcess Order s` p
		INNER JOIN `tabProcess Order Scrap` s ON s.parent = p.name AND s.parenttype = 'Process Order s'
			AND s.parentfield = 'process_definition_scrap'
		{where_clause}

		ORDER BY process_order_id, sort_order, child_idx
		""",
		values * 3,
		as_dict=True,
	)


def get_batch_rows(process_order_ids: list[str], filters: dict) -> list[dict]:
	if not process_order_ids:
		return []

	conditions = ["b.process_order IN %(process_order_ids)s"]
	values = {"process_order_ids": tuple(set(process_order_ids))}

	if filters.get("department"):
		conditions.append("b.department = %(department)s")
		values["department"] = filters.get("department")
	if filters.get("project"):
		conditions.append("b.project = %(project)s")
		values["project"] = filters.get("project")

	where_clause = "WHERE " + " AND ".join(conditions)
	return frappe.db.sql(
		f"""
		SELECT b.name AS batch_order_id, b.process_order, b.process_type AS batch_process_type,
			b.date AS batch_date, b.time AS batch_time, b.status AS batch_status,
			b.department AS batch_department, b.project AS batch_project, b.cost_center AS batch_cost_center,
			'Raw' AS item_type, r.item_code, r.qty, r.rate, r.amount, r.warehouse,
			'raw' AS row_color, 1 AS sort_order, r.idx AS child_idx
		FROM `tabBatch Order s` b
		INNER JOIN `tabProcess Batch raw` r ON r.parent = b.name AND r.parenttype = 'Batch Order s'
			AND r.parentfield = 'process_definition_raw'
		{where_clause}

		UNION ALL

		SELECT b.name AS batch_order_id, b.process_order, b.process_type AS batch_process_type,
			b.date AS batch_date, b.time AS batch_time, b.status AS batch_status,
			b.department AS batch_department, b.project AS batch_project, b.cost_center AS batch_cost_center,
			'Finish' AS item_type, f.item_code, f.qty, f.rate, f.amount, f.warehouse,
			'finish' AS row_color, 2 AS sort_order, f.idx AS child_idx
		FROM `tabBatch Order s` b
		INNER JOIN `tabProcess Batch Finish` f ON f.parent = b.name AND f.parenttype = 'Batch Order s'
			AND f.parentfield = 'process_definition_finish'
		{where_clause}

		UNION ALL

		SELECT b.name AS batch_order_id, b.process_order, b.process_type AS batch_process_type,
			b.date AS batch_date, b.time AS batch_time, b.status AS batch_status,
			b.department AS batch_department, b.project AS batch_project, b.cost_center AS batch_cost_center,
			'Scrap' AS item_type, s.item_code, s.qty, s.rate, s.amount, s.warehouse,
			'scrap' AS row_color, 3 AS sort_order, s.idx AS child_idx
		FROM `tabBatch Order s` b
		INNER JOIN `tabProcess Batch Scrap` s ON s.parent = b.name AND s.parenttype = 'Batch Order s'
			AND s.parentfield = 'process_definition_scrap'
		{where_clause}

		ORDER BY batch_order_id, sort_order, child_idx
		""",
		values,
		as_dict=True,
	)


def get_stock_entry_rows(batch_order_ids: list[str]) -> list[dict]:
	if not batch_order_ids:
		return []

	return frappe.db.sql(
		"""
		SELECT
			se.name AS stock_entry_id,
			se.custom_batch_order_id AS batch_order_id,
			se.posting_date AS stock_posting_date,
			se.posting_time AS stock_posting_time,
			se.purpose AS stock_purpose,
			se.stock_entry_type,
			CASE se.docstatus WHEN 0 THEN 'Draft' WHEN 1 THEN 'Submitted' WHEN 2 THEN 'Cancelled' END AS stock_status,
			CASE
				WHEN EXISTS (
					SELECT 1 FROM `tabProcess Batch Scrap` bs
					WHERE bs.parent = se.custom_batch_order_id AND bs.item_code = sed.item_code
				) THEN 'Scrap'
				WHEN sed.is_scrap_item = 1 THEN 'Scrap'
				WHEN EXISTS (
					SELECT 1 FROM `tabProcess Batch Finish` bf
					WHERE bf.parent = se.custom_batch_order_id AND bf.item_code = sed.item_code
				) THEN 'Finish'
				WHEN sed.is_finished_item = 1 OR sed.t_warehouse IS NOT NULL THEN 'Finish'
				ELSE 'Raw'
			END AS item_type,
			sed.item_code,
			sed.qty,
			sed.basic_rate AS rate,
			sed.amount,
			sed.s_warehouse,
			sed.t_warehouse,
			CASE
				WHEN EXISTS (
					SELECT 1 FROM `tabProcess Batch Scrap` bs
					WHERE bs.parent = se.custom_batch_order_id AND bs.item_code = sed.item_code
				) THEN 'scrap'
				WHEN sed.is_scrap_item = 1 THEN 'scrap'
				WHEN EXISTS (
					SELECT 1 FROM `tabProcess Batch Finish` bf
					WHERE bf.parent = se.custom_batch_order_id AND bf.item_code = sed.item_code
				) THEN 'finish'
				WHEN sed.is_finished_item = 1 OR sed.t_warehouse IS NOT NULL THEN 'finish'
				ELSE 'raw'
			END AS row_color,
			sed.idx AS child_idx
		FROM `tabStock Entry` se
		INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
		WHERE se.custom_batch_order_id IN %(batch_order_ids)s
		ORDER BY se.name, sed.idx
		""",
		{"batch_order_ids": tuple(set(batch_order_ids))},
		as_dict=True,
	)


def blank_repeated_headers(data: list[dict]) -> list[dict]:
	previous = {"order": None, "batch": None, "stock": None}
	header_fields = {
		"order": ("process_order_id", "order_date", "order_process_type", "order_department", "order_project", "process_order_qty"),
		"batch": ("batch_order_id", "batch_process_type", "batch_date", "batch_time", "batch_status", "batch_department", "batch_project", "batch_cost_center"),
		"stock": ("stock_entry_id", "stock_posting_date", "stock_posting_time", "stock_purpose", "stock_entry_type", "stock_status"),
	}
	id_fields = {"order": "process_order_id", "batch": "batch_order_id", "stock": "stock_entry_id"}

	for row in data:
		for key, id_field in id_fields.items():
			current = row.get(id_field)
			if current and current == previous[key]:
				for fieldname in header_fields[key]:
					row[fieldname] = ""
			elif current:
				previous[key] = current

	return data
