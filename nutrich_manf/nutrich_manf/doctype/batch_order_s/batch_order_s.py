
# ============================================================================================================================

# Copyright (c) 2024, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, add_months, nowtime
from frappe.desk.query_report import generate_report_result as get_report
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt 
from frappe import _
from erpnext.stock.doctype.batch.batch import get_batch_qty
from nutrich_manf.nutrich_manf.doctype.process_order_s.process_order_s import (
	get_batch_order_qty_for_process,
)



class BatchOrders(Document):

	def before_insert(self):
		if not self.status:
			self.status = "Not Start"

	@frappe.whitelist()
	def update_cost(self):
		self._validate_batch_required()
		self.process_defination_raw_amount()
		self.calculatate_cost()
		self.process_definition_finish_amount()
		self.calculate_process_definition_scrap_amount()
		self.calculate_total_out_qty_amount()
		self.flags.ignore_validate_update_after_submit = True
		frappe.logger().error("Update Cost Method Called")
		self.save()
    
	def before_save(self):
		self._validate_batch_required()
		self.process_defination_raw_amount()
		self.calculatate_cost()
		self.update_per_kg_cost()
		self.process_definition_finish_amount()
		self.calculate_process_definition_scrap_amount()
		self.validate_batch_qty()


		self.calculate_total_out_qty_amount()
		self.validate_process_order_batch_qty()
	
	def validate_batch_qty(self):
		for row in self.process_definition_raw:
			if row.item_code and row.batch:
				batch_qty = frappe.db.get_value("Batch", row.batch, "batch_qty")
				if batch_qty < row.qty:
					frappe.throw(_("Batch {0} quantity {1} is less than required quantity {2} for item {3} in row {4} (Raw Material In (Batch)).").format(row.batch, batch_qty, row.qty, row.item_code, row.idx))

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
			
		for idx, row in enumerate(self.process_definition_scrap or [], start=1):
			if not row.item_code:
				continue
			has_batch = frappe.get_cached_value("Item", row.item_code, "has_batch_no")
			if has_batch and not row.batch: 
				missing.append(f"Scrap row {idx}: Item {row.item_code}")

		if missing:
			frappe.throw(
				"Batch is mandatory for items:<br>"
				+ "<br>".join(missing)
			)

	def on_update(self):
		self.sync_process_order_progress()

	def on_submit(self):
		self.sync_process_order_progress()
		self.validate_is_group_warehouse()
		self.validate_raw_material_stock_availability()

	def on_cancel(self):
		self.sync_process_order_progress()

	def on_trash(self):
		self.sync_process_order_progress()
	
	def validate_is_group_warehouse(self):
		for row in self.process_definition_raw:
			if row.warehouse:
				warehouse_type = frappe.get_value("Warehouse", row.warehouse, "is_group")
				# frappe.throw(str(warehouse_type))	
				if warehouse_type == 1:
					frappe.throw(_("Group node warehouse {0} in row {1} (Raw Material In (Batch)) is not allowed to select for transaction.").format(row.warehouse, row.idx))
		
		for row in self.process_definition_finish:
			if row.warehouse:
				warehouse_type = frappe.get_value("Warehouse", row.warehouse, "is_group")
				# frappe.throw(str(warehouse_type))	
				if warehouse_type == 1:
					frappe.throw(_("Group node warehouse {0} in row {1} (Finish Items Out (Batch)) is not allowed to select for transaction.").format(row.warehouse, row.idx))
		
		for row in self.process_definition_scrap:
			if row.warehouse:
				warehouse_type = frappe.get_value("Warehouse", row.warehouse, "is_group")
				# frappe.throw(str(warehouse_type))	
				if warehouse_type == 1:
					frappe.throw(_("Group node warehouse {0} in row {1} (Scrap Items Out (Batch)) is not allowed to select for transaction.").format(row.warehouse, row.idx))

	def validate_raw_material_stock_availability(self):
		required_qty_map = {}
		row_map = {}

		for row in self.process_definition_raw or []:
			if not row.item_code or not row.warehouse:
				continue

			key = (row.item_code, row.warehouse, row.batch or "")
			required_qty_map[key] = flt(required_qty_map.get(key)) + flt(row.qty)
			row_map.setdefault(key, []).append(str(row.idx))

		shortages = []
		precision = self.precision("total_raw_qty") or 3

		for (item_code, warehouse, batch), required_qty in required_qty_map.items():
			if batch:
				available_qty = get_batch_qty(
					batch_no=batch,
					warehouse=warehouse,
					item_code=item_code,
					posting_date=self.date,
					posting_time=self.time or nowtime(),
				)
			else:
				available_qty = frappe.db.get_value(
					"Bin",
					{
						"item_code": item_code,
						"warehouse": warehouse,
					},
					"actual_qty",
				) or 0

			if flt(available_qty, precision) < flt(required_qty, precision):
				shortages.append(
					_(
						"Rows {0}: Item {1}, Warehouse {2}{3} - Available Qty is {4}, Required Qty is {5}."
					).format(
						", ".join(row_map.get((item_code, warehouse, batch), [])),
						item_code,
						warehouse,
						_(", Batch {0}").format(batch) if batch else "",
						flt(available_qty, precision),
						flt(required_qty, precision),
					)
				)

		if shortages:
			frappe.throw(
				_("Raw material stock is not available for Batch Order:<br>{0}").format(
					"<br>".join(shortages)
				)
			)

	@frappe.whitelist()
	def create_in_subcontracting(self):
		if not self.process_order:
			frappe.throw(_("Process Order is required to create In Subcontracting."))

		out_subcontracting = frappe.db.get_value(
			"Out Subcontracting s",
			{"process_order": self.process_order, "docstatus": 1},
			[
				"name",
				"supplier",
				"supplier_name",
				"posting_date",
				"posting_time",
				"company",
				"cost_center",
				"total_quantity",
				"outstanding_amount",
			],
			as_dict=True,
			order_by="creation desc",
		)
		if not out_subcontracting:
			frappe.throw(_("No submitted Out Subcontracting found for this Process Order."))

		batch_qty = flt(self.total_raw_qty)
		if batch_qty <= 0:
			frappe.throw(_("Batch Order total raw quantity must be greater than zero."))

		in_qty = batch_qty
		ratio = in_qty / batch_qty if batch_qty else 0

		insub = frappe.new_doc("In Subcontracting s")
		insub.supplier = out_subcontracting.supplier
		insub.supplier_name = out_subcontracting.supplier_name
		insub.posting_date = self.date or out_subcontracting.posting_date
		insub.posting_time = out_subcontracting.posting_time or nowtime()
		insub.company = out_subcontracting.company
		insub.cost_center = self.cost_center or out_subcontracting.cost_center
		insub.department = self.department
		insub.batch_order = self.name
		insub.total_raw_qty = in_qty
		insub.total_raw_amount = flt(self.total_raw_amount) * ratio

		for row in self.process_definition_raw or []:
			adjusted_qty = flt(row.qty) * ratio
			insub.append("in_raw_material", {
				"referance_challan": out_subcontracting.name,
				"item": row.item_code,
				"item_name": row.item_name,
				"rate": row.rate,
				"quantity": adjusted_qty,
				"uom": row.uom,
				"amount": flt(adjusted_qty) * flt(row.rate),
				"batch_no": row.batch,
				"warehouse": row.warehouse,
			})

		for row in self.process_definition_finish or []:
			adjusted_qty = flt(row.qty) * ratio
			insub.append("finish_items", {
				"item_code": row.item_code,
				"item_name": row.item_name,
				"yeild": row.yeild,
				"qty": adjusted_qty,
				"uom": row.uom,
				"rate": row.rate,
				"amount": flt(adjusted_qty) * flt(row.rate),
				"valuation_rate": row.valuation_rate,
				"manufacturing_rate": row.manufacturing_rate,
				"mfg_chart_value": flt(adjusted_qty) * flt(row.manufacturing_rate),
				"basic_value": flt(row.basic_value) * ratio,
				"operation_cost": flt(row.operation_cost) * ratio,
				"total_cost": flt(row.total_cost) * ratio,
				"batch": row.batch,
				"warehouse": row.warehouse,
			})

		return insub

	
	def validate_difference_amount(self):
		if self.difference_amount != self.total_cost or self.difference_amount !=0:
			frappe.throw("Difference Amount must be equal to Total Cost or Zero")

	# def validate_process_order_batch_qty(self):
	# 	if not self.process_order: 
	# 		return

	# 	process_order_qty = frappe.db.get_value("Process Order s", self.process_order, "total_raw_qty")
	# 	if process_order_qty is None:
	# 		return

	# 	used_qty = get_batch_order_qty_for_process(self.process_order, self.name)
	# 	remaining_qty = flt(process_order_qty) - flt(used_qty)
	# 	batch_qty = flt(self.total_raw_qty)

	# 	if batch_qty > remaining_qty:
	# 		frappe.throw(
	# 			_(
	# 				"Remaining quantity for Process Order {0} is {1}. "
	# 				"Batch Order quantity cannot be {2}."
	# 			).format(
	# 				self.process_order,
	# 				flt(max(remaining_qty, 0), self.precision("total_raw_qty")),
	# 				flt(batch_qty, self.precision("total_raw_qty")),
	# 			)
	# 		)

	def validate_process_order_batch_qty(self):
		if not self.process_order:
			return

		process_order_qty = frappe.db.get_value(
			"Process Order s",
			self.process_order,
			"total_raw_qty"
		)

		if process_order_qty is None:
			return

		used_qty = get_batch_order_qty_for_process(
			self.process_order,
			self.name
		)

		precision = self.precision("total_raw_qty") or 3

		process_order_qty = flt(process_order_qty, precision)
		used_qty = flt(used_qty, precision)
		batch_qty = flt(self.total_raw_qty, precision)

		# Round remaining quantity to the same precision
		remaining_qty = flt(process_order_qty - used_qty, precision)

		# Allow tiny floating point differences
		if batch_qty - remaining_qty > (1 / (10 ** precision)):
			frappe.throw(
				_(
					"Remaining quantity for Process Order {0} is {1}. "
					"Batch Order quantity cannot be {2}."
				).format(
					self.process_order,
					remaining_qty,
					batch_qty,
				)
			)

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
	
	# ow.qty = self.quantity * row.yeild / 100
	@frappe.whitelist()
	def update_qty_button(self):
		if self.quantity > 0 and self.process_definition_raw:
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
	# @frappe.whitelist()
	# def process_defination_raw_amount(self):

	# 	total_qty = 0
	# 	total_amount = 0  

	# 	for row in self.process_definition_raw: ##process_definition_raw
	# 		manuf_rate = frappe.get_value("Manufacturing Rate Chart s", {"item_code": row.item_code, "process_type": self.process_type}, "rate") or 0.00
	# 		if self.process_type and row.item_code:
	# 			# frappe.throw(str(manuf_rate))
	# 			row.manufacturing_rate  =  manuf_rate
			
	# 		# if row.item_code and row.warehouse:
	# 		# 	val_rate = frappe.get_value("Bin", {"item_code": row.item_code, "warehouse": row.warehouse}, "valuation_rate") or 0.00
	# 		# 	row.rate = val_rate
	# 		if row.item_code and row.warehouse:
	# 			val_rate = 0.00
	# 			if row.batch:
	# 				val_rate = frappe.get_value(
	# 					"Stock Ledger Entry",
	# 					{"item_code": row.item_code, "warehouse": row.warehouse, "batch_no": row.batch, "is_cancelled": 0},
	# 					"valuation_rate",
	# 					order_by="posting_date desc, posting_time desc, creation desc",
	# 				) or 0.00
	# 				if not val_rate:
	# 					batch_ref = frappe.db.get_value("Batch", row.batch, ["reference_doctype", "reference_name"], as_dict=True)
	# 					if batch_ref and batch_ref.reference_doctype == "Stock Reconciliation":
	# 						val_rate = frappe.get_value(
	# 							"Stock Reconciliation Item",
	# 							{"parent": batch_ref.reference_name, "item_code": row.item_code, "warehouse": row.warehouse, "batch_no": row.batch},
	# 							"valuation_rate",
	# 						) or 0.00
	# 			if not val_rate:
	# 				val_rate = frappe.get_value("Bin", {"item_code": row.item_code, "warehouse": row.warehouse}, "valuation_rate") or 0.00
	# 			row.rate = val_rate

	# 		row.amount = flt((row.qty or 0) * (row.rate or 0), row.precision("amount"))
	# 		total_qty += flt(row.qty)
	# 		total_amount += flt(row.amount)

	# 	self.total_raw_qty = flt(total_qty, self.precision("total_raw_qty"))
	# 	self.total_raw_amount = flt(total_amount, self.precision("total_raw_amount"))
	
	@frappe.whitelist()
	def process_defination_raw_amount(self):

		total_qty = 0
		total_amount = 0

		for row in self.process_definition_raw:

			# Manufacturing Rate
			if self.process_type and row.item_code:
				manuf_rate = frappe.get_value(
					"Manufacturing Rate Chart s",
					{
						"item_code": row.item_code,
						"process_type": self.process_type
					},
					"rate"
				) or 0.00

				row.manufacturing_rate = manuf_rate

			# Fetch Raw Material Rate
			if row.item_code and row.warehouse:

				val_rate = 0.00

				# -----------------------------
				# Batch Selected
				# -----------------------------
				if row.batch:

					# Get valuation rate using Serial & Batch Bundle
					sle = frappe.db.sql("""
						SELECT sle.incoming_rate
						FROM `tabStock Ledger Entry` sle
						INNER JOIN `tabSerial and Batch Entry` sbe
							ON sbe.parent = sle.serial_and_batch_bundle
						WHERE
							sle.item_code = %s
							AND sle.warehouse = %s
							AND sbe.batch_no = %s
							AND sle.is_cancelled = 0
						ORDER BY
							sle.posting_date DESC,
							sle.posting_time DESC,
							sle.creation DESC
						LIMIT 1
					""", (
						row.item_code,
						row.warehouse,
						row.batch
					), as_dict=True)

					if sle:
						val_rate = flt(sle[0].incoming_rate)

					# Stock Reconciliation Fallback
					if not val_rate:
						batch_ref = frappe.db.get_value(
							"Batch",
							row.batch,
							["reference_doctype", "reference_name"],
							as_dict=True
						)

						if (
							batch_ref
							and batch_ref.reference_doctype == "Stock Reconciliation"
						):
							val_rate = frappe.get_value(
								"Stock Reconciliation Item",
								{
									"parent": batch_ref.reference_name,
									"item_code": row.item_code,
									"warehouse": row.warehouse,
									"batch_no": row.batch
								},
								"valuation_rate"
							) or 0.00

				# -----------------------------
				# Bin Fallback
				# -----------------------------
				if not val_rate:
					val_rate = frappe.get_value(
						"Bin",
						{
							"item_code": row.item_code,
							"warehouse": row.warehouse
						},
						"valuation_rate"
					) or 0.00

				row.rate = flt(val_rate, row.precision("rate"))

			# Calculate Amount
			row.amount = flt(
				(row.qty or 0) * (row.rate or 0),
				row.precision("amount")
			)

			total_qty += flt(row.qty)
			total_amount += flt(row.amount)

		self.total_raw_qty = flt(
			total_qty,
			self.precision("total_raw_qty")
		)

		self.total_raw_amount = flt(
			total_amount,
			self.precision("total_raw_amount")
		)
	
	# Process Definition Cost Child Table Calculations------------------------------------------------------------------------------------
	@frappe.whitelist()
	def calculatate_cost(self):
		total_cost = 0
		for row in self.process_definition_cost: #process_definition_cost
			if self.total_raw_qty:
				row.cost = (self.total_raw_qty or 0) * (row.per_kg_cost or 0)
				total_cost += row.cost
		self.total_cost = total_cost

	@frappe.whitelist()
	def update_per_kg_cost(self):
		self.process_defination_raw_amount()
		for row in self.process_definition_cost:
			row.per_kg_cost = row.cost / self.total_raw_qty if self.total_raw_qty else 0
		# self.refresh()

  
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
				# row.qty = (row.yeild / 100) * (self.total_raw_qty or 0)
				row.total_cost = (row.qty or 0) * val_rate

			if row.item_code and row.qty and self.quantity > 0:
				row.yeild = row.qty / self.quantity * 100

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
			row.amount = flt((row.qty or 0) * (row.valuation_rate or 0), row.precision("amount"))
			# row.amount = flt(row.qty) * flt(row.valuation_rate)
			# row.amount = round(flt(row.qty) * flt(row.valuation_rate))

			total_finish_amount += flt(row.amount)

		self.total_finish_amount = flt(total_finish_amount, self.precision("total_finish_amount"))


		# ---------------- OPERATION COST SPLIT ----------------
		if self.total_cost and self.total_finish_amount:
			for row in self.process_definition_finish:
				if row.amount:
					row.operation_cost = (
						row.amount / self.total_finish_amount
					) * self.total_cost
					row.operation_cost = flt(row.operation_cost, row.precision("operation_cost"))
					row.basic_value = flt(row.amount - row.operation_cost, row.precision("basic_value"))



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
				# row.qty = (row.yeild / 100) * (self.total_raw_qty or 0)
				row.total_cost = (row.qty or 0) * val_rate
			
			if row.item_code and row.qty and self.quantity > 0:
				row.yeild = row.qty / self.quantity * 100

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

			row.amount = flt((row.qty or 0) * (row.valuation_rate or 0), row.precision("amount"))

			total_scrap_amount += flt(row.amount)

		self.total_scrap_amount = flt(total_scrap_amount, self.precision("total_scrap_amount"))


		# ---------------- OPERATION COST SPLIT ----------------
		if self.total_cost and self.total_scrap_amount:
			for row in self.process_definition_scrap:
				if row.amount:
					row.operation_cost = (
						row.amount / self.total_scrap_amount
					) * self.total_cost
					row.operation_cost = flt(row.operation_cost, row.precision("operation_cost"))
					row.basic_value = flt(row.amount - row.operation_cost, row.precision("basic_value"))



	# Total Out Qty & Amount Calculations------------------------------------------------------------------------------------	
	@frappe.whitelist()
	def calculate_total_out_qty_amount(self):
		self.total_in_qty = self.total_raw_qty
		# self.total_in_amount = self.total_raw_amount + self.total_cost
		self.total_in_amount = self.total_raw_amount  # Changed By Devika Mam on 29-04-2026

		self.total_out_qty = self.total_finish_qty + self.total_scrap_qty
		self.total_out_material_amount = flt(
			self.total_finish_amount + self.total_scrap_amount,
			self.precision("total_out_material_amount"),
		)

		self.difference_quantity = self.total_raw_qty - self.total_out_qty
		# self.difference_amount = self.total_raw_amount + self.total_cost - self.total_out_material_amount
		self.difference_amount = flt(
			self.total_finish_amount - self.total_raw_amount,
			self.precision("difference_amount"),
		)
 


@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	remaining_qty = get_remaining_stock_entry_raw_qty(source_name)
	if remaining_qty <= 0:
		frappe.throw(_("All raw quantity has already been used in Stock Entries. No remaining quantity available."))

	def set_batch_item_values(source, target, source_parent):
		target.basic_rate = flt(source.get("rate") or source.get("basic_rate") or source.get("valuation_rate"))
		target.basic_amount = flt(source.get("basic_value") or source.get("amount"))
		target.amount = flt(source.get("amount") or source.get("basic_value"))
		target.valuation_rate = (
			flt(source.get("valuation_rate") or target.amount / flt(source.qty)) if flt(source.qty) else 0
		)

	def set_finished_item_values(source, target, source_parent):
		target.is_finished_item = 1
		target.basic_amount = flt(source.get("basic_value") or source.get("amount"))
		target.basic_rate = flt(target.basic_amount / flt(source.qty)) if flt(source.qty) else 0
		target.additional_cost = flt(source.get("operation_cost"))
		target.amount = flt(source.get("amount") or source.get("basic_value"))
		target.valuation_rate = flt(target.amount / flt(source.qty)) if flt(source.qty) else 0

	def set_scrap_item_values(source, target, source_parent):
		target.is_legacy_scrap_item = 1
		set_batch_item_values(source, target, source_parent)

	def postprocess(source, target):
		# Stock Entry defaults
		target.stock_entry_type = "Manufacture"
		target.purpose = "Manufacture"
		target.posting_date = source.date
		target.posting_time = source.time
		target.set_posting_time = 1
		target.custom_batch_order_id = source.name
		target.custom_process_order_id = source.process_order
		target.naming_series = source.manufacturing_naming_series
		ratio = remaining_qty / flt(source.total_raw_qty) if flt(source.total_raw_qty) else 0

		for d in target.items:
			d.qty = flt(d.qty) * ratio
			d.transfer_qty = d.qty
			for fieldname in ("basic_amount", "amount", "additional_cost"):
				if d.meta.has_field(fieldname):
					d.set(fieldname, flt(d.get(fieldname)) * ratio)

		for d in target.additional_costs:
			d.amount = flt(d.amount) * ratio

		# RAW MATERIALS → Source warehouse
		for d in target.items:
			if not d.is_finished_item and not d.is_legacy_scrap_item:
				d.s_warehouse = d.warehouse
				d.t_warehouse = None
				d.transfer_qty = d.qty
				d.conversion_factor = 1
				d.set_basic_rate_manually = 1
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
			if d.is_legacy_scrap_item:
				d.t_warehouse = d.warehouse
				d.s_warehouse = None
				d.transfer_qty = d.qty
				d.conversion_factor = 1
				d.set_basic_rate_manually = 1
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
					"uom": "uom",
					"batch": "batch_no",
					"warehouse": "warehouse",

				},
				"postprocess": set_batch_item_values,
			},

			# ---------------- FINISHED ----------------
			"Process Batch Finish": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"item_code": "item_code",
					"qty": "qty",
					# "valuation_rate": "valuation_rate",
					# "operation_cost": "additional_cost",
					"uom": "uom",
					"warehouse": "warehouse",
					"batch": "batch_no",
					# "set_basic_rate_manually": 1,
					# "basic_rate": 
				},
				"postprocess": set_finished_item_values,
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
				},
				"postprocess": set_scrap_item_values,
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

	

def get_stock_entry_raw_qty_for_batch_order(batch_order_name, exclude_stock_entry=None):
	if not batch_order_name:
		return 0

	conditions = [
		"se.docstatus < 2",
		"se.custom_batch_order_id = %s",
		"sed.s_warehouse IS NOT NULL",
		"sed.s_warehouse != ''",
	]
	values = [batch_order_name]
	if exclude_stock_entry:
		conditions.append("se.name != %s")
		values.append(exclude_stock_entry)

	result = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(sed.qty), 0)
		FROM `tabStock Entry` se
		INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
		WHERE {" AND ".join(conditions)}
		""",
		tuple(values),
	)
	return flt(result[0][0]) if result else 0


def sync_batch_order_status(batch_order_name, exclude_stock_entry=None):
	if not batch_order_name or not frappe.db.exists("Batch Order s", batch_order_name):
		return

	filters = {"custom_batch_order_id": batch_order_name}
	if exclude_stock_entry:
		filters["name"] = ["!=", exclude_stock_entry]

	submitted_stock_entry = frappe.db.exists(
		"Stock Entry",
		{**filters, "docstatus": 1},
	)
	if submitted_stock_entry:
		status = "Complete"
	else:
		draft_stock_entry = frappe.db.exists(
			"Stock Entry",
			{**filters, "docstatus": 0},
		)
		status = "In Process" if draft_stock_entry else "Not Start"

	frappe.db.set_value(
		"Batch Order s",
		batch_order_name,
		"status",
		status,
		update_modified=False,
	)


@frappe.whitelist()
def get_remaining_stock_entry_raw_qty(batch_order_name, exclude_stock_entry=None):
	if not batch_order_name:
		return 0

	batch_order_qty = frappe.db.get_value("Batch Order s", batch_order_name, "total_raw_qty")
	used_qty = get_stock_entry_raw_qty_for_batch_order(batch_order_name, exclude_stock_entry)
	return max(flt(batch_order_qty) - flt(used_qty), 0)



