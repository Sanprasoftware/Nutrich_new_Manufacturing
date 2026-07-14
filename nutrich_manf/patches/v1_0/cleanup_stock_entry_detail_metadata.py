import frappe


def execute():
	frappe.delete_doc_if_exists("Property Setter", "Stock Entry Detail-main-field_order")
	frappe.delete_doc_if_exists("Custom Field", "Stock Entry Detail-additional_taxable_value")
	frappe.clear_cache(doctype="Stock Entry Detail")
