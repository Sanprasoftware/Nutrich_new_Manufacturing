# Copyright (c) 2024, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class ProcessDefinitions(Document):
	
	def before_save(self):
		# self._validate_batch_required()
		self.process_defination_raw_amount()
		self.process_definition_finish_amount()
		self.calculate_process_definition_scrap_amount()


		self.calculate_total_out_qty_amount()
		self.calculatate_cost() 

	# def _validate_batch_required(self):
	# 	missing = []

	# 	for idx, row in enumerate(self.process_definition_raw or [], start=1):
	# 		if not row.item_code:
	# 			continue
	# 		has_batch = frappe.get_cached_value("Item", row.item_code, "has_batch_no")
	# 		if has_batch and not row.batch:
	# 			missing.append(f"Raw row {idx}: Item {row.item_code}")

	# 	for idx, row in enumerate(self.process_definition_finish or [], start=1):
	# 		if not row.item_code:
	# 			continue
	# 		has_batch = frappe.get_cached_value("Item", row.item_code, "has_batch_no")
	# 		if has_batch and not row.batch_no:
	# 			missing.append(f"Finish row {idx}: Item {row.item_code}")

		# if missing:
		# 	frappe.throw(
		# 		"Batch is mandatory for items:<br>"
		# 		+ "<br>".join(missing)
		# 	)


	# Process Definition raw Child Table Calculations
	@frappe.whitelist()
	def process_defination_raw_amount(self):

		total_qty = 0
		total_amount = 0 

		for row in self.process_definition_raw:
			if row.qty and row.rate:	
				row.amount = row.qty * row.rate
			manuf_rate = frappe.get_value("Manufacturing Rate Chart s", {"item_code": row.item_code, "process_type": self.process_type}, "rate") or 0.00
			if self.process_type and row.item_code:
				# frappe.throw(str(manuf_rate))
				row.manufacturing_rate  =  manuf_rate
 
			total_qty += (row.qty or 0)
			total_amount += (row.amount or 0)

		self.total_raw_qty = total_qty
		self.total_raw_amount = total_amount
 
	
	# Process Definition Cost Child Table Calculations
	@frappe.whitelist()
	def calculatate_cost(self):
		total_cost = 0
		for row in self.process_definition_cost:
			if self.total_raw_qty:
				row.cost = (self.total_raw_qty or 0) * (row.per_kg_cost or 0)
				total_cost += row.cost
		self.total_cost = total_cost


	# Process Definition Finish Child Table Calculations
	# @frappe.whitelist()
	# def process_definition_finish_amount(self):

	# 	total_finish_qty = 0
	# 	total_finish_amount = 0
	# 	total_qty_rate = 0 

	# 	for row in self.process_definition_finish:	
	# 		val_rate = frappe.get_value("Bin", {"item_code": row.item_code, "warehouse": row.warehouse}, "valuation_rate") or 0.00
	# 		manuf_rate = frappe.get_value("Manufacturing Rate Chart s", {"item_code": row.item_code, "process_type": self.process_type}, "rate") or 0.00

	# 		if row.item_code and row.yeild:
	# 			row.qty = row.yeild /100 * self.total_raw_qty
	# 			row.total_cost = (row.qty or 0) * (val_rate or 0)

	# 		if self.process_type and row.item_code:
	# 			qty_rate = row.qty * manuf_rate
	# 			total_qty_rate += qty_rate

	# 			# row.amount = row.qty * val_rate

	# 		if row.item_code and row.warehouse:	
	# 			row.valuation_rate = val_rate
				

	# 		if self.process_type and row.item_code:
	# 			row.manufacturing_rate = manuf_rate
	# 			row.mfg_chart_value = (row.qty or 0) * (row.manufacturing_rate or 0)

	# 		total_finish_qty += (row.qty or 0)
	# 		total_finish_amount += (row.amount or 0)
	# 	self.total_finish_qty = total_finish_qty
	# 	self.total_finish_amount = total_finish_amount


	# 	for row in self.process_definition_finish:
	# 		manuf_rate = frappe.get_value(
	# 			"Manufacturing Rate Chart s",
	# 			{"item_code": row.item_code, "process_type": self.process_type},
	# 			"rate"
	# 		) or 0

	# 		qty_rate = (row.qty or 0) * manuf_rate

	# 		if total_qty_rate:
	# 			row.share_percentage = (qty_rate / total_qty_rate) * 100
	# 		else:
	# 			row.share_percentage = 0
		
	# 	if self.total_cost and self.total_finish_amount:
	# 		for row in self.process_definition_finish:
	# 			if row.amount:
	# 				row.operation_cost = (row.amount / self.total_finish_amount) * self.total_cost
	# 				row.basic_value = row.amount - row.operation_cost

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



	# Process Definition Scrap Child Table
	# @frappe.whitelist()
	# def calculate_process_definition_scrap_amount(self):
	# 	total_scrap_qty = 0
	# 	total_scrap_amount = 0
	# 	for row in self.process_definition_scrap:
	# 		val_rate = frappe.get_value("Bin", {"item_code": row.item_code, "warehouse": row.warehouse}, "valuation_rate") or 0.00
	# 		manuf_rate = frappe.get_value("Manufacturing Rate Chart s", {"item_code": row.item_code, "process_type": self.process_type}, "rate") or 0.00

	# 		if row.item_code and row.yeild:
	# 			row.qty = row.yeild/100 * self.total_raw_qty
	# 			row.amount = row.qty * row.rate			
	# 			row.total_cost = (row.qty or 0) * (val_rate or 0)
			
	# 		if row.item_code and row.warehouse:
	# 			row.valuation_rate = val_rate

	# 		if self.process_type and row.item_code:
	# 			row.manufacturing_rate = manuf_rate
	# 			row.sale_rate = (row.qty or 0) * (row.manufacturing_rate or 0)

	# 		total_scrap_qty += (row.qty or 0)
	# 		total_scrap_amount += (row.amount or 0) 
	# 	self.total_scrap_qty = total_scrap_qty
	# 	self.total_scrap_amount = total_scrap_amount

	# 	if self.total_cost and self.total_scrap_amount:
	# 		for row in self.process_definition_scrap:
	# 			if row.amount:
	# 				row.operation_cost = (row.amount / self.total_scrap_amount) * self.total_cost
	# 				row.basic_value = row.amount - row.operation_cost


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


	
	@frappe.whitelist()
	def calculate_total_out_qty_amount(self):
		self.total_in_qty = self.total_raw_qty
		# self.total_in_amount = self.total_raw_amount + self.total_cost
		self.total_in_amount = self.total_raw_amount  # Changed By Devika Mam on 29-04-2026

		self.total_out_qty = self.total_finish_qty + self.total_scrap_qty
		self.total_out_material_amount = self.total_finish_amount + self.total_scrap_amount

		# self.difference_quantity = self.total_finish_qty + self.total_scrap_qty - self.total_raw_qty
		self.difference_quantity = self.total_raw_qty - self.total_out_qty
		# self.difference_amount = self.total_raw_amount + self.total_cost - self.total_out_material_amount
		self.difference_amount = self.total_finish_amount - self.total_raw_amount 
		# if self.difference_quantity != 0.00 or self.difference_amount != 0.00:
		#     frappe.throw("Difference Quantity and Difference Amount must be 0")





@frappe.whitelist()
def make_process_order(source_name, target_doc=None):
    return get_mapped_doc(
        "Process Definition s",
        source_name,
        {
            "Process Definition s": {
                "doctype": "Process Order s",
                "field_map": {
                    "date": "date",
                    "process_type": "process_type",
                    "total_out_qty": "process_order_qty",
                    "total_raw_qty": "total_raw_qty",
                    "total_raw_amount": "total_raw_amount",
                    "total_cost": "total_cost",
                    "total_finish_qty": "total_finish_qty",
                    "total_finish_amount": "total_finish_amount",
                    "total_scrap_qty": "total_scrap_qty",
                    "total_scrap_amount": "total_scrap_amount",
                    "total_out_material_amount": "total_out_material_amount",
                    "difference_quantity": "difference_quantity",
                    "difference_amount": "difference_amount",
                    "name": "process_definition",
                },
            },

            # RAW
            "Process Definition raw": {
                "doctype": "Process Order raw",
            },  

            # COST
            "Process Definition Cost": {
                "doctype": "Process Order Cost",
            },

            # FINISH
            "Process Definition Finish": {
                "doctype": "Process Order Finish",
            },

            # SCRAP
            "Process Definition Scrap": {
                "doctype": "Process Order Scrap",
            },
        },
        target_doc,
    )
 