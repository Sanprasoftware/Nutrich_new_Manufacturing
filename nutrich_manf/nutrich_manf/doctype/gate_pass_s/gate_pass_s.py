# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GatePasss(Document):
	@frappe.whitelist()
	def get_reference_items(self, reference_doctype, reference):
		return _build_reference_items(reference_doctype, reference)


@frappe.whitelist()
def get_reference_items(reference_doctype, reference):
	# Backward-compat for any cached JS still calling the module path.
	return _build_reference_items(reference_doctype, reference)


@frappe.whitelist()
def get_gate_pass_payload(reference_doctype, reference):
	return {
		"reference_doctype": reference_doctype,
		"reference": reference,
		"items": _build_reference_items(reference_doctype, reference),
	}


@frappe.whitelist()
def make_gate_pass(source_name, reference_doctype=None, target_doc=None):
	reference_doctype = reference_doctype or "Process Order s"
	payload = get_gate_pass_payload(reference_doctype, source_name)

	doc = frappe.new_doc("Gate Pass s")
	doc.reference_doctype = payload.get("reference_doctype")
	doc.reference = payload.get("reference")
	doc.set("gate_pass_items", [])

	for row in payload.get("items") or []:
		doc.append(
			"gate_pass_items",
			{
				"item_code": row.get("item_code"),
				"item_name": row.get("item_name"),
				"quantity": row.get("quantity"),
				"uom": row.get("uom"),
			},
		)

	return doc


def _build_reference_items(reference_doctype, reference):
	allowed = {
		"Delivery Note": {"child_table": "items"},
		"Purchase Order": {"child_table": "items"},
		"Sales Invoice": {"child_table": "items"},
		"Stock Entry": {"child_table": "items"},
		"Process Order s": {"child_table": "process_definition_raw"},
	}

	if reference_doctype not in allowed:
		frappe.throw(f"Unsupported Reference Doctype: {reference_doctype}")

	doc = frappe.get_doc(reference_doctype, reference)
	child_table = allowed[reference_doctype]["child_table"]
	rows = doc.get(child_table) or []

	items = []
	for row in rows:
		items.append(
			{
				"item_code": row.get("item_code"),
				"item_name": row.get("item_name"),
				"quantity": row.get("qty"),
				"uom": row.get("uom"),
			}
		)

	return items
