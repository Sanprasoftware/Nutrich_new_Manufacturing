# Copyright (c) 2026, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.document import Document
from frappe import _



class OutSubcontractings(Document): 
	def validate(self):
		self._calculate_totals()
		self.validate_process_order_qty()
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

	def validate_process_order_qty(self):
		if not self.process_order:
			return

		process_order_qty = frappe.db.get_value("Process Order s", self.process_order, "total_raw_qty")
		if process_order_qty is None:
			return

		used_qty = get_out_subcontracting_qty_for_process_order(self.process_order, self.name)
		remaining_qty = flt(process_order_qty) - flt(used_qty)
		current_qty = flt(self.total_quantity)

		if current_qty > remaining_qty:
			frappe.throw(
				_(
					"Remaining quantity for Process Order {0} is {1}. "
					"Out Subcontracting quantity cannot be {2}."
				).format(
					self.process_order,
					flt(max(remaining_qty, 0), self.precision("total_quantity")),
					flt(current_qty, self.precision("total_quantity")),
				)
			)
	
	def create_stock_entry(self):
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.naming_series = "MTR/.FY./.#"
		stock_entry.stock_entry_type = "Sub Contracting Out"
		stock_entry.posting_date = self.posting_date
		stock_entry.posting_time = self.posting_time
		stock_entry.company = self.company
		stock_entry.cost_center = self.cost_center
		stock_entry.custom_out_subcontracting_id = self.name

		for idx, item in enumerate(self.items or [], start=1):
			if not item.source_warehouse or not item.target_warehouse:
				frappe.throw(
					_("Source and Target Warehouse are mandatory for Out Subcontracting row {0}.").format(idx)
				)

			stock_entry.append("items", {
				"item_code": item.item,
				"qty": item.quantity,
				"uom": item.uom,
				"basic_rate": item.rate,
				"basic_amount": flt(item.quantity) * flt(item.rate),
				"batch_no": item.batch_no,
				"conversion_factor": 1,
				"s_warehouse": item.source_warehouse,
				"t_warehouse": item.target_warehouse,
				"cost_center": self.cost_center,
			})

		stock_entry.insert()
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
		SELECT COALESCE(SUM(raw.quantity), 0)
		FROM `tabMaterial Items s` raw
		INNER JOIN `tabIn Subcontracting s` insub ON insub.name = raw.parent
		WHERE insub.docstatus < 2
			AND raw.parenttype = 'In Subcontracting s'
			AND raw.referance_challan = %s
		""",
		(out_subcontracting_name,),
	)
	return flt(result[0][0]) if result else 0


def get_out_subcontracting_qty_for_process_order(process_order_name, exclude_out_subcontracting=None):
	if not process_order_name:
		return 0

	conditions = ["docstatus < 2", "process_order = %s"]
	values = [process_order_name]
	if exclude_out_subcontracting:
		conditions.append("name != %s")
		values.append(exclude_out_subcontracting)

	result = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(total_quantity), 0)
		FROM `tabOut Subcontracting s`
		WHERE {" AND ".join(conditions)}
		""",
		tuple(values),
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
