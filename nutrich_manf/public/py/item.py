import frappe

@frappe.whitelist()
def validate_item(doc, method=None):
    if doc.is_stock_item == 0 and doc.is_fixed_asset == 0 and not doc.item_defaults:
        frappe.throw("Please Select Item Defaults Tables Default Expense Account or Default Income Account")
    
    if doc.is_stock_item == 0 and doc.is_fixed_asset == 0:
        for row in doc.item_defaults:
            if not row.expense_account and not row.income_account:
                frappe.throw("Please Select Item Defaults Tables Default Expense Account or Default Income Account")