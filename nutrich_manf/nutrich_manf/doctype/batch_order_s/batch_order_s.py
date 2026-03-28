
# ============================================================================================================================

# Copyright (c) 2024, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, add_months
from frappe.desk.query_report import generate_report_result as get_report
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt



class BatchOrders(Document):
    
	def before_save(self):
		self._validate_batch_required()
		self.process_defination_raw_amount()
		self.process_definition_finish_amount()
		self.calculate_process_definition_scrap_amount()


		self.calculate_total_out_qty_amount()
		self.calculatate_cost()

	def _validate_batch_required(self):
		missing = []

		for idx, row in enumerate(self.process_definition_raw or [], start=1):
			if not row.item_code:
				continue
			has_batch = frappe.get_cached_value("Item", row.item_code, "has_batch_no")
			if has_batch and not row.batch:
				missing.append(f"Raw row {idx}: Item {row.item_code}")

		for idx, row in enumerate(self.process_definition_finish or [], start=1):
			if not row.item_code:
				continue
			has_batch = frappe.get_cached_value("Item", row.item_code, "has_batch_no")
			if has_batch and not row.batch: 
				missing.append(f"Finish row {idx}: Item {row.item_code}")

		if missing:
			frappe.throw(
				"Batch is mandatory for items:<br>"
				+ "<br>".join(missing)
			)

	def on_update(self):
		self.sync_process_order_progress()

	def on_submit(self):
		self.sync_process_order_progress()

	def on_cancel(self):
		self.sync_process_order_progress()

	def on_trash(self):
		self.sync_process_order_progress()

	def sync_process_order_progress(self):
		if not self.process_order:
			return

		process_order = frappe.db.get_value(
			"Process Order s",
			self.process_order,
			["name", "total_in_qty"],
			as_dict=True,
		)
		if not process_order:
			return

		result = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(total_in_qty), 0)
			FROM `tabBatch Order s`
			WHERE docstatus < 2 AND process_order = %s
			""",
			(self.process_order,),
		)
		completed_qty = flt(result[0][0]) if result else 0
		if process_order.total_in_qty:
			per_completed = min((completed_qty / process_order.total_in_qty) * 100, 100)
		else:
			per_completed = 0

		frappe.db.set_value(
			"Process Order s",
			self.process_order,
			"per_completed",
			flt(per_completed, 2),
			update_modified=False,
		)
	
	@frappe.whitelist()
	def update_qty_button(self):
		if self.quantity and self.process_definition_raw:
			for row in self.process_definition_raw:
				row.qty = self.quantity * row.yeild / 100 
			self.process_defination_raw_amount()

		if self.quantity and self.process_definition_finish:
			for row in self.process_definition_finish:
				row.qty = self.quantity * row.yeild / 100
			self.process_definition_finish_amount()
		
		if self.quantity and self.process_definition_scrap:
			for row in self.process_definition_scrap:
				row.qty = self.quantity * row.yeild / 100
			self.calculate_process_definition_scrap_amount()
		

		self.calculate_total_out_qty_amount()
		self.calculatate_cost()

 
	# Process Definition raw Child Table Calculations
	@frappe.whitelist()
	def process_defination_raw_amount(self):

		total_qty = 0
		total_amount = 0 

		for row in self.process_definition_raw: ##process_definition_raw
			if row.qty and row.rate:	
				row.amount = row.qty * row.rate
			
			manuf_rate = frappe.get_value("Manufacturing Rate Chart s", {"item_code": row.item_code, "process_type": self.process_type}, "rate") or 0.00
			if self.process_type and row.item_code:
				# frappe.throw(str(manuf_rate))
				row.manufacturing_rate  =  manuf_rate
			
			if row.item_code and row.warehouse:
				val_rate = frappe.get_value("Bin", {"item_code": row.item_code, "warehouse": row.warehouse}, "valuation_rate") or 0.00
				row.rate = val_rate

			total_qty += (row.qty or 0)
			total_amount += (row.amount or 0)

		self.total_raw_qty = total_qty
		self.total_raw_amount = total_amount
 
	
	# Process Definition Cost Child Table Calculations------------------------------------------------------------------------------------
	@frappe.whitelist()
	def calculatate_cost(self):
		total_cost = 0
		for row in self.process_definition_cost: #process_definition_cost
			if self.total_raw_qty:
				row.cost = (self.total_raw_qty or 0) * (row.per_kg_cost or 0)
				total_cost += row.cost
		self.total_cost = total_cost

  
	# Process Definition Finish Child Table Calculations------------------------------------------------------------------------------------
	@frappe.whitelist()
	def process_definition_finish_amount(self):

		total_finish_qty = 0
		total_finish_amount = 0
		total_qty_rate = 0

		# ---------------- FIRST LOOP: QTY & TOTAL QTY*RATE ----------------
		for row in self.process_definition_finish:
			val_rate = frappe.get_value(
				"Bin",
				{"item_code": row.item_code, "warehouse": row.warehouse},
				"valuation_rate"
			) or 0

			manuf_rate = frappe.get_value(
				"Manufacturing Rate Chart s",
				{"item_code": row.item_code, "process_type": self.process_type},
				"rate"
			) or 0

			if row.item_code and row.yeild:
				row.qty = (row.yeild / 100) * (self.total_raw_qty or 0)
				row.total_cost = (row.qty or 0) * val_rate

			if self.process_type and row.item_code:
				row.manufacturing_rate = manuf_rate
				qty_rate = (row.qty or 0) * manuf_rate
				total_qty_rate += qty_rate
				row.mfg_chart_value = qty_rate
				row.rate = row.basic_value / row.qty if row.qty else 0

			total_finish_qty += (row.qty or 0)

		self.total_finish_qty = total_finish_qty


		# ---------------- TOTAL INPUT AMOUNT ----------------
		total_in_amt = (self.total_raw_amount or 0) + (self.total_cost or 0)


		# ---------------- SECOND LOOP: SHARE, RATE, AMOUNT ----------------
		for row in self.process_definition_finish:
			manuf_rate = row.manufacturing_rate or 0
			qty_rate = (row.qty or 0) * manuf_rate

			if total_qty_rate:
				share = qty_rate / total_qty_rate
			else:
				share = 0

			row.share_percentage = share * 100

			# allocated amount for this row
			process_amt = total_in_amt * share

			# per unit valuation rate
			if row.qty:
				row.valuation_rate = process_amt / row.qty
			else:
				row.valuation_rate = 0

			# final row amount
			row.amount = (row.qty or 0) * (row.valuation_rate or 0)

			total_finish_amount += (row.amount or 0)

		self.total_finish_amount = total_finish_amount


		# ---------------- OPERATION COST SPLIT ----------------
		if self.total_cost and self.total_finish_amount:
			for row in self.process_definition_finish:
				if row.amount:
					row.operation_cost = (
						row.amount / self.total_finish_amount
					) * self.total_cost
					row.basic_value = row.amount - row.operation_cost



	# Process Definition Scrap Child Table Calculations------------------------------------------------------------------------------------
	@frappe.whitelist()
	def calculate_process_definition_scrap_amount(self):

		total_scrap_qty = 0
		total_scrap_amount = 0
		total_qty_rate = 0

		# ---------------- FIRST LOOP: QTY & TOTAL QTY*RATE ----------------
		for row in self.process_definition_scrap:
			val_rate = frappe.get_value(
				"Bin",
				{"item_code": row.item_code, "warehouse": row.warehouse},
				"valuation_rate"
			) or 0

			manuf_rate = frappe.get_value(
				"Manufacturing Rate Chart s",
				{"item_code": row.item_code, "process_type": self.process_type},
				"rate"
			) or 0

			if row.item_code and row.yeild:
				row.qty = (row.yeild / 100) * (self.total_raw_qty or 0)
				row.total_cost = (row.qty or 0) * val_rate

			if self.process_type and row.item_code:
				row.manufacturing_rate = manuf_rate
				qty_rate = (row.qty or 0) * manuf_rate
				total_qty_rate += qty_rate
				row.mfg_chart_value = qty_rate

			if row.item_code and row.warehouse:
				row.valuation_rate = val_rate

			total_scrap_qty += (row.qty or 0)

		self.total_scrap_qty = total_scrap_qty


		# ---------------- TOTAL INPUT AMOUNT ----------------
		total_in_amt = (self.total_raw_amount or 0) + (self.total_cost or 0)


		# ---------------- SECOND LOOP: SHARE, RATE, AMOUNT ----------------
		for row in self.process_definition_scrap:
			manuf_rate = row.manufacturing_rate or 0
			qty_rate = (row.qty or 0) * manuf_rate

			if total_qty_rate:
				share = qty_rate / total_qty_rate
			else:
				share = 0
 
			row.share_percentage = share * 100

			# allocated amount for this scrap row
			process_amt = total_in_amt * share

			if row.qty:
				row.valuation_rate = process_amt / row.qty
			else:
				row.valuation_rate = 0

			row.amount = (row.qty or 0) * (row.valuation_rate or 0)

			total_scrap_amount += (row.amount or 0)

		self.total_scrap_amount = total_scrap_amount


		# ---------------- OPERATION COST SPLIT ----------------
		if self.total_cost and self.total_scrap_amount:
			for row in self.process_definition_scrap:
				if row.amount:
					row.operation_cost = (
						row.amount / self.total_scrap_amount
					) * self.total_cost
					row.basic_value = row.amount - row.operation_cost



	# Total Out Qty & Amount Calculations------------------------------------------------------------------------------------	
	@frappe.whitelist()
	def calculate_total_out_qty_amount(self):
		self.total_in_qty = self.total_raw_qty
		self.total_in_amount = self.total_raw_amount + self.total_cost

		self.total_out_qty = self.total_finish_qty + self.total_scrap_qty
		self.total_out_material_amount = self.total_finish_amount + self.total_scrap_amount

		self.difference_quantity = self.total_raw_qty - self.total_out_qty
		# self.difference_amount = self.total_raw_amount + self.total_cost - self.total_out_material_amount
		self.difference_amount = self.total_finish_amount - self.total_raw_amount 



@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):

	def postprocess(source, target):
		# Stock Entry defaults
		target.stock_entry_type = "Manufacture"
		# target.posting_date = source.date
		target.custom_batch_order_id = source.name
		target.naming_series = source.manufacturing_naming_series

		# RAW MATERIALS → Source warehouse
		for d in target.items:
			if not d.is_finished_item and not d.is_scrap_item:
				d.s_warehouse = d.warehouse
				d.t_warehouse = None
				d.transfer_qty = d.qty
				d.conversion_factor = 1
				d.allow_zero_valuation = 1

		# FINISHED ITEMS → Target warehouse
		for d in target.items:
			if d.is_finished_item:
				d.t_warehouse = d.warehouse
				d.s_warehouse = None
				d.transfer_qty = d.qty
				d.conversion_factor = 1
				# d.basic_rate = d.basic_value / d.qty if d.qty else 0
				d.set_basic_rate_manually = 1
				d.allow_zero_valuation = 1

		# SCRAP ITEMS
		for d in target.items:
			if d.is_scrap_item:
				d.t_warehouse = d.warehouse
				d.s_warehouse = None
				d.transfer_qty = d.qty
				d.conversion_factor = 1
				d.allow_zero_valuation_rate = 1

	return get_mapped_doc(
		"Batch Order s",
		source_name,
		{
			# ---------------- PARENT ----------------
			"Batch Order s": {
				"doctype": "Stock Entry",
			},

			# ---------------- RAW ----------------
			"Process Batch raw": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"item_code": "item_code",
					"qty": "qty",
					# "basic_rate": "rate",
					"amount": "amount", 
					"uom": "uom",
					"batch": "batch_no",
					"warehouse": "warehouse",

				},
			},

			# ---------------- FINISHED ----------------
			"Process Batch Finish": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"item_code": "item_code",
					"qty": "qty",
					"rate": "basic_rate",
					"basic_value": "basic_amount",
					"valuation_rate": "valuation_rate",
					"operation_cost": "additional_cost",
					"uom": "uom",
					"warehouse": "warehouse",
					"batch": "batch_no",
					# "set_basic_rate_manually": 1,
					# "basic_rate": 
				},
				"postprocess": lambda src, tgt, src_parent: setattr(tgt, "is_finished_item", 1),
			},

			# ---------------- SCRAP ----------------
			"Process Batch Scrap": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"item_code": "item_code",
					"qty": "qty",
					"uom": "uom",
					"warehouse": "warehouse",
					"batch": "batch_no",
					# "basic_rate": "rate",
				},
				"postprocess": lambda src, tgt, src_parent: setattr(tgt, "is_scrap_item", 1),
			},

			# ---------------- ADDITIONAL COST ----------------
			"Process Batch Cost": {
				"doctype": "Landed Cost Taxes and Charges",
				"field_map": {
					"operation": "expense_account",
					"cost": "amount",
				},
				"postprocess": lambda src, tgt, src_parent: setattr(
					tgt, "description", src.operation or "Additional Cost"
				),
			},
		},
		target_doc,
		postprocess=postprocess,
	)
