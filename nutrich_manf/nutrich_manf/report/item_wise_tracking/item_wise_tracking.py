import frappe
# Python Script Report (report.py)

def execute(filters=None):
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
    warehouse = filters.get("warehouse")
    
    conditions = ""
    if warehouse:
        conditions += f" AND sle.warehouse = '{warehouse}'"
    
    query = f"""
        SELECT 
            sle.item_code,
            i.item_name,
            
            -- Opening Balance (before from_date)
            SUM(CASE WHEN sle.posting_date < '{from_date}' THEN sle.actual_qty ELSE 0 END) as opening_qty,
            SUM(CASE WHEN sle.posting_date < '{from_date}' THEN sle.stock_value_difference ELSE 0 END) as opening_value,
            
            -- Purchase Receipt
            SUM(CASE WHEN sle.voucher_type = 'Purchase Receipt' AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN sle.actual_qty ELSE 0 END) as pr_qty,
            SUM(CASE WHEN sle.voucher_type = 'Purchase Receipt' AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN sle.stock_value_difference ELSE 0 END) as pr_value,
            
            -- Delivery Note
            SUM(CASE WHEN sle.voucher_type = 'Delivery Note' AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN ABS(sle.actual_qty) ELSE 0 END) as dn_qty,
            SUM(CASE WHEN sle.voucher_type = 'Delivery Note' AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN ABS(sle.stock_value_difference) ELSE 0 END) as dn_value,
            
            -- Manufacturing Stock In
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Manufacture' AND sle.actual_qty > 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN sle.actual_qty ELSE 0 END) as mfg_in_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Manufacture' AND sle.actual_qty > 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN sle.stock_value_difference ELSE 0 END) as mfg_in_value,
            
            -- Manufacturing Stock Out
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Manufacture' AND sle.actual_qty < 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN ABS(sle.actual_qty) ELSE 0 END) as mfg_out_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Manufacture' AND sle.actual_qty < 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN ABS(sle.stock_value_difference) ELSE 0 END) as mfg_out_value,
            
            -- Repack Stock In
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Repack' AND sle.actual_qty > 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN sle.actual_qty ELSE 0 END) as repack_in_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Repack' AND sle.actual_qty > 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN sle.stock_value_difference ELSE 0 END) as repack_in_value,
            
            -- Repack Stock Out
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Repack' AND sle.actual_qty < 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN ABS(sle.actual_qty) ELSE 0 END) as repack_out_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type = 'Repack' AND sle.actual_qty < 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN ABS(sle.stock_value_difference) ELSE 0 END) as repack_out_value,
            
            -- Others Stock In
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type NOT IN ('Manufacture', 'Repack') AND sle.actual_qty > 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN sle.actual_qty ELSE 0 END) as others_in_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type NOT IN ('Manufacture', 'Repack') AND sle.actual_qty > 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN sle.stock_value_difference ELSE 0 END) as others_in_value,
            
            -- Others Stock Out
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type NOT IN ('Manufacture', 'Repack') AND sle.actual_qty < 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN ABS(sle.actual_qty) ELSE 0 END) as others_out_qty,
            SUM(CASE WHEN sle.voucher_type = 'Stock Entry' AND se.stock_entry_type NOT IN ('Manufacture', 'Repack') AND sle.actual_qty < 0 AND sle.posting_date BETWEEN '{from_date}' AND '{to_date}' THEN ABS(sle.stock_value_difference) ELSE 0 END) as others_out_value
            
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabItem` i ON sle.item_code = i.name
        LEFT JOIN `tabStock Entry` se ON sle.voucher_no = se.name AND sle.voucher_type = 'Stock Entry'
        WHERE sle.is_cancelled = 0 {conditions}
        GROUP BY sle.item_code, i.item_name
        HAVING ABS(opening_qty) > 0 OR ABS(pr_qty) > 0 OR ABS(dn_qty) > 0 
            OR ABS(mfg_in_qty) > 0 OR ABS(mfg_out_qty) > 0 
            OR ABS(repack_in_qty) > 0 OR ABS(repack_out_qty) > 0
            OR ABS(others_in_qty) > 0 OR ABS(others_out_qty) > 0
    """
    
    data = frappe.db.sql(query, as_dict=True)
    
    # Calculate closing balances
    for row in data:
        row.closing_qty = (row.opening_qty or 0) + (row.pr_qty or 0) - (row.dn_qty or 0) + \
                          (row.mfg_in_qty or 0) - (row.mfg_out_qty or 0) + \
                          (row.repack_in_qty or 0) - (row.repack_out_qty or 0) + \
                          (row.others_in_qty or 0) - (row.others_out_qty or 0)
                          
        row.closing_value = (row.opening_value or 0) + (row.pr_value or 0) - (row.dn_value or 0) + \
                            (row.mfg_in_value or 0) - (row.mfg_out_value or 0) + \
                            (row.repack_in_value or 0) - (row.repack_out_value or 0) + \
                            (row.others_in_value or 0) - (row.others_out_value or 0)
    
    return data