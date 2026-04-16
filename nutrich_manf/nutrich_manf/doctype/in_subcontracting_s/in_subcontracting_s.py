# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InSubcontractings(Document):
	def validate(self):
		self.calculate_totals()
	
	def on_submit(self):
		self.create_stock_entry()

	def calculate_totals(self):
		total_qty = 0.0
		total_amount = 0.0 

		for row in self.in_raw_material or []: 
			qty = row.quantity or 0.0
			rate = row.rate or 0.0
			amount = qty * rate  

			row.amount = amount

			total_qty += qty
			total_amount += amount

		self.total_raw_qty = total_qty
		self.total_raw_amount = total_amount
	
	@frappe.whitelist()
	def calculate_finished_items_calculate_totals(self):
		total_qty = 0.0
		total_amount = 0.0 

		for row in self.finished_items or []: 
			qty = row.qty or 0.0
			rate = row.rate or 0.0
			amount = qty * rate  

			row.amount = amount

			total_qty += qty
			total_amount += amount

		self.total_qty = total_qty
		self.total_finished_amount = total_amount

	
	def create_stock_entry(self):
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = "Sub Contracting In"
		stock_entry.custom_in_subcontracting_id = self.name
		
		for row in self.in_raw_material:
			stock_entry.append("items", {
				"s_warehouse": row.warehouse,
				"item_code": row.item ,
				"item_name": row.item_name,
				"qty": row.quantity,
				"basic_rate": row.rate,
				"basic_amount": row.amount,
				"batch_no": row.batch_no,
			})
		for row in self.finished_items:
			stock_entry.append("items", {
				"t_warehouse": row.warehouse,
				"item_code": row.finished_item ,
				"item_name": row.finished_item_name,
				"qty": row.qty,
				"basic_rate": row.rate,
				"basic_amount": row.amount,
				"batch_no": row.batch_no,
			})
		stock_entry.save()