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
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.posting_date = self.posting_date
		stock_entry.posting_time = self.posting_time
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