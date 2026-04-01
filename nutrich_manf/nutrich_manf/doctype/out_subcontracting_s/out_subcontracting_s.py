# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.document import Document


class OutSubcontractings(Document): 
	def validate(self):
		self._calculate_totals()
	def on_submit(self):
		self.create_stock_entry()

	def _calculate_totals(self):
		total_qty = 0.0
		total_amount = 0.0 

		for row in self.items or []: 
			qty = flt(row.quantity) 
			rate = flt(row.rate)

			if not row.amount and (qty or rate):
				row.amount = flt(qty * rate)

			total_qty += qty
			total_amount += flt(row.amount)

		self.total_quantity = total_qty
		self.total_amount = total_amount
		self.rounded_total = flt(total_amount, 0)
		self.outstanding_amount = total_amount

	def _get_base_amount(self, row):
		qty = flt(row.quantity)
		rate = flt(row.rate)
		if qty or rate:
			return flt(qty * rate)
		return flt(row.amount)
	
	def create_stock_entry(self):
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.naming_series = "MTR/.FY./.#"
		stock_entry.stock_entry_type = "Sub Contracting Out"
		stock_entry.posting_date = self.posting_date
		stock_entry.posting_time = self.posting_time
		stock_entry.custom_out_subcontracting_id = self.name
		# stock_entry.from_warehouse = self.from_warehouse
		# stock_entry.to_warehouse = self.to_warehouse
		for item in self.items:
			stock_entry.append("items", {
				"item_code": item.item,
				"qty": item.quantity,
				"uom": item.uom,
				"basic_rate": item.rate,
				"batch_no": item.batch_no,
				"conversion_factor": "1",
				"s_warehouse": item.source_warehouse,
				"t_warehouse": item.target_warehouse
			})
		stock_entry.save()				
		stock_entry.submit()

	def _get_department_details_for_in_subcontracting(self):
		department_name = None

		if self.process_order:
			department_name = frappe.db.get_value("Process Order s", self.process_order, "department")

		if not department_name and self.source_warehouse and self.target_warehouse:
			department_name = frappe.db.get_value(
				"Manufacturing Department s",
				{
					"source_warehouse": self.source_warehouse,
					"target_warehouse": self.target_warehouse,
				},
				"name",
			)

		if not department_name:
			return None

		department_doc = frappe.get_cached_doc("Manufacturing Department s", department_name)
		return {
			"department": department_doc.name,
			"source_warehouse": department_doc.source_warehouse,
			"target_warehouse": department_doc.target_warehouse,
			"wip_warehuse": department_doc.wip_warehouse,
		}

	@frappe.whitelist()
	def create_in_subcontracting(self):

		insub = frappe.new_doc("In Subcontracting s")
		insub.supplier = self.supplier
		insub.supplier_name = self.supplier_name
		insub.posting_date = self.posting_date
		insub.posting_time = self.posting_time
		insub.company = self.company
		insub.cost_center = self.cost_center
		insub.target_warehouse = self.target_warehouse
		insub.source_warehouse = self.source_warehouse
		insub.out_subcontracting_id = self.name

		for row in self.items:
			insub.append("in_raw_material", {
				"referance_challan": insub.name,
				"item": row.item,
				"yeild": row.get("yield"),
				"rate": row.rate,
				"uom": row.uom,
				"quantity": row.quantity,
				# "production_done_quantity": row.quantity,
				# "manufacturing_rate": row.rate,
				# "basic_value": row.amount,
				# "sale_value": row.amount,
				# "operation_cost": row.operation_cost,
				# "valuation_rate": row.valuation_rate,
				# "total_cost": row.total_cost,
				# "batch_no": row.batch_no,
				# "warehouse": row.source_warehouse
			})

		return insub
