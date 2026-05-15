# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from nutrich_manf.nutrich_manf.doctype.out_subcontracting_s.out_subcontracting_s import (
	update_out_subcontracting_progress,
)


class InSubcontractings(Document):
	def validate(self):
		self.calculate_totals()
	
	def on_submit(self):
		self.create_stock_entry()
		self.sync_out_subcontracting_progress()

	def on_update(self):
		self.sync_out_subcontracting_progress()

	def on_cancel(self):
		self.sync_out_subcontracting_progress()

	def on_trash(self):
		self.sync_out_subcontracting_progress()

	def calculate_totals(self):
		total_qty = 0.0
		total_amount = 0.0
		total_finished_qty = 0.0
		total_finished_amount = 0.0 

		for row in self.in_raw_material or []: 
			qty = row.quantity or 0.0
			rate = row.rate or 0.0
			amount = qty * rate  

			row.amount = amount

			total_qty += qty
			total_amount += amount
		
		for row in self.finish_items or []:
			qty = row.qty or 0.0
			rate = row.valuation_rate or 0.0
			amount = qty * rate  

			row.amount = amount

			total_finished_qty += qty
			total_finished_amount += amount

		self.total_raw_qty = total_qty
		self.total_raw_amount = total_amount
		self.total_qty = total_finished_qty
		self.total_finished_amount = total_finished_amount

	@frappe.whitelist()
	def calculate_finished_items_calculate_totals(self):
		total_qty = 0.0
		total_amount = 0.0 

		for row in self.finish_items or []: 
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
		
		# for row in self.in_raw_material:
		# 	stock_entry.append("items", {
		# 		"s_warehouse": row.warehouse,
		# 		"item_code": row.item ,
		# 		"item_name": row.item_name,
		# 		"qty": row.quantity,
		# 		"basic_rate": row.rate,
		# 		"basic_amount": row.amount,
		# 		"batch_no": row.batch_no,
		# 	})
		for row in self.finish_items:
			stock_entry.append("items", {
				# "t_warehouse": row.warehouse,
				"s_warehouse": self.source_warehouse,
				"t_warehouse": self.target_warehouse,
				"item_code": row.item_code ,
				"item_name": row.item_name,
				"qty": row.qty,
				"basic_rate": row.rate,
				"basic_amount": row.amount,
				"batch_no": row.batch,
				"set_basic_rate_manually": 1
			})
		stock_entry.save()

	def sync_out_subcontracting_progress(self):
		if self.out_subcontracting_id:
			update_out_subcontracting_progress(self.out_subcontracting_id)
