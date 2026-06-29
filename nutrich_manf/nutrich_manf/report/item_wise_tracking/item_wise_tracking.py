import frappe
# Python Script Report (report.py)

def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": "Opening Balance Qty", "fieldname": "opening_qty", "fieldtype": "Float", "width": 140},
        {"label": "Opening Balance Value", "fieldname": "opening_value", "fieldtype": "Currency", "width": 150},
        {"label": "Purchase Receipt Qty", "fieldname": "pr_qty", "fieldtype": "Float", "width": 150},
        {"label": "Purchase Receipt Value", "fieldname": "pr_value", "fieldtype": "Currency", "width": 150},
        {"label": "Delivery Note Qty", "fieldname": "dn_qty", "fieldtype": "Float", "width": 140},
        {"label": "Delivery Note Value", "fieldname": "dn_value", "fieldtype": "Currency", "width": 150},
        {"label": "Stock In Qty (Mfg)", "fieldname": "mfg_in_qty", "fieldtype": "Float", "width": 140},
        {"label": "Stock In Value (Mfg)", "fieldname": "mfg_in_value", "fieldtype": "Currency", "width": 150},
        {"label": "Stock Out Qty (Mfg)", "fieldname": "mfg_out_qty", "fieldtype": "Float", "width": 150},
        {"label": "Stock Out Value (Mfg)", "fieldname": "mfg_out_value", "fieldtype": "Currency", "width": 160},
        {"label": "Stock In Qty (Repack)", "fieldname": "repack_in_qty", "fieldtype": "Float", "width": 150},
        {"label": "Stock In Value (Repack)", "fieldname": "repack_in_value", "fieldtype": "Currency", "width": 160},
        {"label": "Stock Out Qty (Repack)", "fieldname": "repack_out_qty", "fieldtype": "Float", "width": 160},
        {"label": "Stock Out Value (Repack)", "fieldname": "repack_out_value", "fieldtype": "Currency", "width": 170},
        {"label": "Stock In Qty (Others)", "fieldname": "others_in_qty", "fieldtype": "Float", "width": 150},
        {"label": "Stock In Value (Others)", "fieldname": "others_in_value", "fieldtype": "Currency", "width": 160},
        {"label": "Stock Out Qty (Others)", "fieldname": "others_out_qty", "fieldtype": "Float", "width": 160},
        {"label": "Stock Out Value (Others)", "fieldname": "others_out_value", "fieldtype": "Currency", "width": 170},
        {"label": "Closing Balance Qty", "fieldname": "closing_qty", "fieldtype": "Float", "width": 150},
        {"label": "Closing Balance Value", "fieldname": "closing_value", "fieldtype": "Currency", "width": 160},
    ]

def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    conditions = ["sle.is_cancelled = 0"]
    values = {"from_date": from_date, "to_date": to_date}

    if filters.get("warehouse"):
        conditions.append("sle.warehouse = %(warehouse)s")
        values["warehouse"] = filters.warehouse

    if filters.get("warehouse_group"):
        wh = frappe.db.get_value("Warehouse", filters.warehouse_group, ["lft", "rgt"], as_dict=True)
        if wh:
            conditions.append("""
                sle.warehouse IN (
                    SELECT name FROM `tabWarehouse`
                    WHERE lft >= %(warehouse_lft)s AND rgt <= %(warehouse_rgt)s
                )
            """)
            values.update({"warehouse_lft": wh.lft, "warehouse_rgt": wh.rgt})

    if filters.get("item_code"):
        conditions.append("sle.item_code = %(item_code)s")
        values["item_code"] = filters.item_code

    if filters.get("item_group"):
        group = frappe.db.get_value("Item Group", filters.item_group, ["lft", "rgt"], as_dict=True)
        if group:
            conditions.append("""
                i.item_group IN (
                    SELECT name FROM `tabItem Group`
                    WHERE lft >= %(item_group_lft)s AND rgt <= %(item_group_rgt)s
                )
            """)
            values.update({"item_group_lft": group.lft, "item_group_rgt": group.rgt})

    if filters.get("project"):
        conditions.append("(sle.project = %(project)s OR pri.project = %(project)s OR dni.project = %(project)s OR se.project = %(project)s OR sed.project = %(project)s)")
        values["project"] = filters.project

    if filters.get("cost_center"):
        conditions.append("(pri.cost_center = %(cost_center)s OR dni.cost_center = %(cost_center)s OR se.cost_center = %(cost_center)s OR sed.cost_center = %(cost_center)s)")
        values["cost_center"] = filters.cost_center

    query = """
        SELECT
            sle.item_code,
            i.item_name,
            SUM(CASE WHEN sle.posting_date < %(from_date)s THEN sle.actual_qty ELSE 0 END) as opening_qty,
            SUM(CASE WHEN sle.posting_date < %(from_date)s THEN sle.stock_value_difference ELSE 0 END) as opening_value,
            SUM(CASE WHEN sle.voucher_type = 'Purchase Receipt' AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN sle.actual_qty ELSE 0 END) as pr_qty,
            SUM(CASE WHEN sle.voucher_type = 'Purchase Receipt' AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN COALESCE(pri.base_amount, pri.amount, sle.stock_value_difference) ELSE 0 END) as pr_value,
            SUM(CASE WHEN sle.voucher_type = 'Delivery Note' AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN ABS(sle.actual_qty) ELSE 0 END) as dn_qty,
            SUM(CASE WHEN sle.voucher_type = 'Delivery Note' AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN COALESCE(dni.base_amount, dni.amount, ABS(sle.stock_value_difference)) ELSE 0 END) as dn_value,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Manufacture' AND sed.is_finished_item = 1 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN ABS(sle.actual_qty) ELSE 0 END) as mfg_in_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Manufacture' AND sed.is_finished_item = 1 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN ABS(COALESCE(sed.basic_amount, sed.amount, sle.stock_value_difference)) ELSE 0 END) as mfg_in_value,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Manufacture' AND IFNULL(sed.is_finished_item, 0) = 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN -ABS(sle.actual_qty) ELSE 0 END) as mfg_out_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Manufacture' AND IFNULL(sed.is_finished_item, 0) = 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN -ABS(COALESCE(sed.basic_amount, sed.amount, sle.stock_value_difference)) ELSE 0 END) as mfg_out_value,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Repack' AND sed.is_finished_item = 1 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN ABS(sle.actual_qty) ELSE 0 END) as repack_in_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Repack' AND sed.is_finished_item = 1 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN ABS(COALESCE(sed.basic_amount, sed.amount, sle.stock_value_difference)) ELSE 0 END) as repack_in_value,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Repack' AND IFNULL(sed.is_finished_item, 0) = 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN -ABS(sle.actual_qty) ELSE 0 END) as repack_out_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Repack' AND IFNULL(sed.is_finished_item, 0) = 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN -ABS(COALESCE(sed.basic_amount, sed.amount, sle.stock_value_difference)) ELSE 0 END) as repack_out_value,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type NOT IN ('Manufacture', 'Repack') AND sle.actual_qty > 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN sle.actual_qty ELSE 0 END) as others_in_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type NOT IN ('Manufacture', 'Repack') AND sle.actual_qty > 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN COALESCE(sed.basic_amount, sed.amount, sle.stock_value_difference) ELSE 0 END) as others_in_value,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type NOT IN ('Manufacture', 'Repack') AND sle.actual_qty < 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN sle.actual_qty ELSE 0 END) as others_out_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type NOT IN ('Manufacture', 'Repack') AND sle.actual_qty < 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN -ABS(COALESCE(sed.basic_amount, sed.amount, sle.stock_value_difference)) ELSE 0 END) as others_out_value,
            SUM(CASE WHEN sle.posting_date <= %(to_date)s THEN sle.actual_qty ELSE 0 END) as closing_qty,
            SUM(CASE WHEN sle.posting_date <= %(to_date)s THEN sle.stock_value_difference ELSE 0 END) as closing_value
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabItem` i ON sle.item_code = i.name
        LEFT JOIN `tabStock Entry` se ON sle.voucher_no = se.name AND sle.voucher_type = 'Stock Entry'
        LEFT JOIN `tabStock Entry Detail` sed ON sle.voucher_detail_no = sed.name AND sle.voucher_type = 'Stock Entry'
        LEFT JOIN `tabPurchase Receipt Item` pri ON sle.voucher_detail_no = pri.name AND sle.voucher_type = 'Purchase Receipt'
        LEFT JOIN `tabDelivery Note Item` dni ON sle.voucher_detail_no = dni.name AND sle.voucher_type = 'Delivery Note'
        WHERE {conditions}
        GROUP BY sle.item_code, i.item_name
        HAVING ABS(opening_qty) > 0 OR ABS(pr_qty) > 0 OR ABS(dn_qty) > 0
            OR ABS(mfg_in_qty) > 0 OR ABS(mfg_out_qty) > 0
            OR ABS(repack_in_qty) > 0 OR ABS(repack_out_qty) > 0
            OR ABS(others_in_qty) > 0 OR ABS(others_out_qty) > 0
    """.format(conditions=" AND ".join(conditions))

    data = frappe.db.sql(query, values, as_dict=True)

    for row in data:
        row.closing_qty = row.closing_qty or 0
        row.closing_value = row.closing_value or 0

    return data
