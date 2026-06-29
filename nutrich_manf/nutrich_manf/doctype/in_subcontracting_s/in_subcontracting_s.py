# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


class InSubcontractings(Document):
	def validate(self):
		self.calculate_totals()
		self.validate_batch_order_qty()
	
	def on_submit(self):
		self.create_stock_entry()

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

	def validate_batch_order_qty(self):
		batch_order = self.get("batch_order")
		if not batch_order:
			return

		batch_order_qty = frappe.db.get_value("Batch Order s", batch_order, "total_raw_qty")
		if batch_order_qty is None:
			return

		used_qty = get_in_subcontracting_qty_for_batch_order(batch_order, self.name)
		remaining_qty = flt(batch_order_qty) - flt(used_qty)
		current_qty = flt(self.total_raw_qty)
		if current_qty > remaining_qty:
			frappe.throw(
				_(
					"Remaining quantity for Batch Order {0} is {1}. "
					"In Subcontracting total raw quantity cannot be {2}."
				).format(
					batch_order,
					flt(max(remaining_qty, 0), self.precision("total_raw_qty")),
					flt(current_qty, self.precision("total_raw_qty")),
				)
			)

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
		stock_entry.naming_series = "MTR/.FY./.#"
		stock_entry.stock_entry_type = "Sub Contracting In"
		stock_entry.posting_date = self.posting_date
		stock_entry.posting_time = self.posting_time
		stock_entry.company = self.company
		stock_entry.cost_center = self.cost_center
		stock_entry.from_warehouse = self.source_warehouse
		stock_entry.to_warehouse = self.target_warehouse
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
		for row in self.finish_items or []:
			stock_entry.append("items", {
				"s_warehouse": self.source_warehouse,
				"t_warehouse": self.target_warehouse,
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": row.qty,
				"basic_rate": row.rate or row.valuation_rate,
				"basic_amount": row.amount,
				"batch_no": row.batch,
				"conversion_factor": 1,
				"cost_center": self.cost_center,
				"set_basic_rate_manually": 1,
			})

		stock_entry.insert()
		stock_entry.submit()


def get_in_subcontracting_qty_for_batch_order(batch_order, exclude_in_subcontracting=None):
	if not batch_order:
		return 0

	conditions = ["docstatus < 2", "batch_order = %s"]
	values = [batch_order]
	if exclude_in_subcontracting:
		conditions.append("name != %s")
		values.append(exclude_in_subcontracting)

	result = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(total_raw_qty), 0)
		FROM `tabIn Subcontracting s`
		WHERE {" AND ".join(conditions)}
		""",
		tuple(values),
	)
	return flt(result[0][0]) if result else 0
