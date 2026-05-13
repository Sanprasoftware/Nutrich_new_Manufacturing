# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.document import Document



class OutSubcontractings(Document): 
	def validate(self):
		self._calculate_totals()
		self.set_per_received()

	def on_submit(self):
		self.create_stock_entry()


	def _calculate_totals(self):
		total_qty = 0.0
		total_amount = 0.0 

		for row in self.items or []: 
			qty = flt(row.quantity) 
			rate = flt(row.rate)

			# if not row.amount and (qty or rate):
			# 	row.amount = flt(qty * rate)
			if row.rate and row.rate:
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
		stock_entry.cost_center = self.cost_center
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

	def set_per_received(self):
		received_qty = get_received_qty_from_in_subcontracting(self.name)
		if self.total_quantity:
			self.per_received = min((received_qty / self.total_quantity) * 100, 100)
		else:
			self.per_received = 0

def get_received_qty_from_in_subcontracting(out_subcontracting_name):
	if not out_subcontracting_name:
		return 0

	result = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(total_raw_qty), 0)
		FROM `tabIn Subcontracting s`
		WHERE docstatus < 2 AND out_subcontracting_id = %s
		""",
		(out_subcontracting_name,),
	)
	return flt(result[0][0]) if result else 0


def update_out_subcontracting_progress(out_subcontracting_name):
	if not out_subcontracting_name:
		return

	out_subcontracting = frappe.db.get_value(
		"Out Subcontracting s",
		out_subcontracting_name,
		["name", "total_quantity"],
		as_dict=True,
	)
	if not out_subcontracting:
		return

	received_qty = get_received_qty_from_in_subcontracting(out_subcontracting_name)
	if out_subcontracting.total_quantity:
		per_received = min((received_qty / out_subcontracting.total_quantity) * 100, 100)
	else:
		per_received = 0

	frappe.db.set_value(
		"Out Subcontracting s",
		out_subcontracting_name,
		"per_received",
		flt(per_received, 2),
		update_modified=False,
	)
