# Copyright (c) 2024, Sanpra and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, add_months
from frappe.desk.query_report import generate_report_result as get_report
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc
from frappe import _


class ProcessOrders(Document):
    
	def before_save(self):
		self._validate_batch_required()
		self.process_defination_raw_amount()
		self.process_definition_finish_amount()
		self.calculate_process_definition_scrap_amount() 

 
		self.calculate_total_out_qty_amount() 
		self.calculatate_cost()
		self.set_per_completed()
 
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



	@frappe.whitelist()
	def update_qty_button(self):
		if self.process_order_qty and self.process_definition_raw:
			for row in self.process_definition_raw:
				row.qty = self.process_order_qty * row.yeild / 100
			self.process_defination_raw_amount()

		if self.process_order_qty and self.process_definition_finish:
			for row in self.process_definition_finish:
				row.qty = self.process_order_qty * row.yeild / 100
			self.process_definition_finish_amount()
		
		if self.process_order_qty and self.process_definition_scrap:
			for row in self.process_definition_scrap:
				row.qty = self.process_order_qty * row.yeild / 100
			self.calculate_process_definition_scrap_amount()
		

		self.calculate_total_out_qty_amount()
		self.calculatate_cost()
		self.set_per_completed()
 
	# Process Definition raw Child Table Calculations
	@frappe.whitelist()
	def process_defination_raw_amount(self):

		total_qty = 0
		total_amount = 0  

		for row in self.process_definition_raw: ##process_definition_raw
			if row.qty and row.rate:	
				row.amount = row.qty * row.rate
				# row.amount = flt(row.qty) * flt(row.rate)
			
			manuf_rate = frappe.get_value("Manufacturing Rate Chart s", {"item_code": row.item_code, "process_type": self.process_type}, "rate") or 0.00
			if self.process_type and row.item_code:
				# frappe.throw(str(manuf_rate))
				row.manufacturing_rate  =  manuf_rate
			
			# if row.item_code and row.warehouse:
			# 	val_rate = frappe.get_value("Bin", {"item_code": row.item_code, "warehouse": row.warehouse}, "valuation_rate") or 0.00
			# 	row.rate = val_rate
			if row.item_code and row.warehouse:
				val_rate = 0.00
				if row.batch:
					val_rate = frappe.get_value(
						"Stock Ledger Entry",
						{"item_code": row.item_code, "warehouse": row.warehouse, "batch_no": row.batch, "is_cancelled": 0},
						"valuation_rate",
						order_by="posting_date desc, posting_time desc, creation desc",
					) or 0.00
					if not val_rate:
						batch_ref = frappe.db.get_value("Batch", row.batch, ["reference_doctype", "reference_name"], as_dict=True)
						if batch_ref and batch_ref.reference_doctype == "Stock Reconciliation":
							val_rate = frappe.get_value(
								"Stock Reconciliation Item",
								{"parent": batch_ref.reference_name, "item_code": row.item_code, "warehouse": row.warehouse, "batch_no": row.batch},
								"valuation_rate",
							) or 0.00
				if not val_rate:
					val_rate = frappe.get_value("Bin", {"item_code": row.item_code, "warehouse": row.warehouse}, "valuation_rate") or 0.00
				row.rate = val_rate

			total_qty += (row.qty or 0)
			total_amount += (row.amount or 0)

		self.total_raw_qty = total_qty
		self.total_raw_amount = total_amount
 
 
	
	# Process Definition Cost Child Table Calculations------------------------------------------------------------------------------------
	@frappe.whitelist()
	def calculatate_cost(self):
		per_kg_cost = 0
		total_cost = 0
		for row in self.process_definition_cost: #process_definition_cost
			if self.total_raw_qty:
				row.cost = (self.total_raw_qty or 0) * (row.per_kg_cost or 0)
				total_cost += row.cost
				per_kg_cost += row.per_kg_cost or 0
		self.total_cost = total_cost
		self.per_kg_cost = per_kg_cost


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



	# @frappe.whitelist()
	# def process_definition_finish_amount(self):

	# 	from frappe.desk.query_report import run as run_report
	# 	from frappe.utils import today, add_months

	# 	company = frappe.defaults.get_user_default("Company")
	# 	to_date = today()
	# 	from_date = add_months(to_date, -3)

	# 	for row in self.process_definition_finish:

	# 		if not row.item_code or not row.warehouse:
	# 			continue

	# 		# ---------------- RUN STOCK LEDGER REPORT ----------------
	# 		result = run_report(
	# 			"Stock Ledger",
	# 			filters={
	# 				"company": company,
	# 				"from_date": from_date,
	# 				"to_date": to_date,
	# 				"item": row.item_code,
	# 				"warehouse": row.warehouse,
	# 				"batch_no": row.batch or None,
	# 			},
	# 			ignore_prepared_report=True
	# 		)

	# 		data = result.get("result") or []
	# 		columns = result.get("columns") or []

	# 		if len(data) <= 2:
	# 			frappe.msgprint(
	# 				f"No Stock Ledger data found for Item {row.item_code}"
	# 			)
	# 			continue

				
	# 		latest_row = data[1]
		
	# 		valuation_rate = latest_row["valuation_rate"]  # Assuming valuation_rate is the 5th column
	# 		row.valuation_rate = valuation_rate
	# 		# frappe.throw(str(valuation_rate))
			



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
		# self.total_out_qty = self.total_finish_qty + self.total_scrap_qty
		# self.total_out_material_amount = self.total_finish_amount + self.total_scrap_amount

		# # self.difference_quantity = self.total_finish_qty + self.total_scrap_qty - self.total_raw_qty
		# self.difference_quantity = self.total_raw_qty - self.total_out_qty
		# self.difference_amount = self.total_raw_amount + self.total_cost - self.total_out_material_amount


		# -----------------------------------------------------------------
		self.total_in_qty = self.total_raw_qty
		# self.total_in_amount = self.total_raw_amount + self.total_cost
		self.total_in_amount = self.total_raw_amount  # Changed By Devika Mam on 29-04-2026

		self.total_out_qty = self.total_finish_qty + self.total_scrap_qty
		self.total_out_material_amount = self.total_finish_amount + self.total_scrap_amount

		# self.difference_quantity = self.total_finish_qty + self.total_scrap_qty - self.total_raw_qty
		self.difference_quantity = self.total_raw_qty - self.total_out_qty
		# self.difference_amount = self.total_raw_amount + self.total_cost - self.total_out_material_amount
		self.difference_amount = self.total_finish_amount - self.total_raw_amount 

	def set_per_completed(self):
		completed_qty = get_completed_qty_from_batch_orders(self.name)
		if self.total_in_qty:
			self.per_completed = min((completed_qty / self.total_in_qty) * 100, 100)
		else:
			self.per_completed = 0
	 

@frappe.whitelist()
def make_batch_order(source_name, target_doc=None):
    remaining_qty = get_remaining_batch_order_qty(source_name)
    if remaining_qty <= 0:
        frappe.throw(_("All quantity has already been used in Batch Orders. No remaining quantity available."))

    def _scale_child_rows(rows, ratio):
        for row in rows or []:
            for fieldname in (
                "qty",
                "amount",
                "cost",
                "basic_value",
                "operation_cost",
                "total_cost",
                "mfg_chart_value",
            ):
                if row.meta.has_field(fieldname):
                    row.set(fieldname, flt(row.get(fieldname)) * ratio)

    def _postprocess(source, target):
        original_qty = flt(source.total_raw_qty)
        ratio = remaining_qty / original_qty if original_qty else 0

        target.quantity = remaining_qty
        target.total_raw_qty = remaining_qty

        _scale_child_rows(target.process_definition_raw, ratio)
        _scale_child_rows(target.process_definition_cost, ratio)
        _scale_child_rows(target.process_definition_finish, ratio)
        _scale_child_rows(target.process_definition_scrap, ratio)

        for fieldname in (
            "total_raw_amount",
            "total_cost",
            "total_finish_qty",
            "total_finish_amount",
            "total_scrap_qty",
            "total_scrap_amount",
            "total_out_material_amount",
            "difference_quantity",
            "difference_amount",
        ):
            if target.meta.has_field(fieldname):
                target.set(fieldname, flt(target.get(fieldname)) * ratio)

        target.total_in_qty = remaining_qty

    return get_mapped_doc(
        "Process Order s",
        source_name,
        {
            "Process Order s": {
                "doctype": "Batch Order s",
                "field_map": {
                    "date": "date",
                    "process_type": "process_type",
                    "name": "process_order",
                    "process_definition": "process_definition",
                    "department": "department",
                    "project": "project",

                    # "total_out_qty": "process_order_qty",
                    "process_order_qty": "process_order_qty",
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
                },
            },

            # RAW
            "Process Order raw": {
                "doctype": "Process Batch raw",
            },

            # COST
            "Process Order Cost": {
                "doctype": "Process Batch Cost",
            },

            # FINISH
            "Process Order Finish": {
                "doctype": "Process Batch Finish",
            },

            # SCRAP
            "Process Order Scrap": {
                "doctype": "Process Batch Scrap",
            },
        },
        target_doc,
        postprocess=_postprocess,
    )


# @frappe.whitelist()
# def make_out_subcontracting(source_name, target_doc=None):
# 	def _postprocess(source, target):
# 		target.process_order = source.name
# 		if not target.posting_date:
# 			target.posting_date = source.date

# 		for row in target.items or []:
# 			row.process_order_id = source.name

# 	return get_mapped_doc(
# 		"Process Order s",
# 		source_name,
# 		{
# 			"Process Order s": {
# 				"doctype": "Out Subcontracting s",
# 				"field_map": {
# 					"name": "process_order",
# 					"date": "posting_date",
# 				},
# 			},
# 			"Process Order raw": {
# 				"doctype": "Out Subcontracting Item s",
# 				"field_map": {
# 					"item_code": "item",
# 					"item_name": "item_name",
# 					"qty": "quantity",
# 					"yeild": "yield",
# 					"uom": "uom",
# 					"rate": "rate",
# 					"amount": "amount",
# 					"batch": "batch_no",
# 					"warehouse": "source_warehouse",
# 				},
# 			},
# 		},
# 		target_doc,
# 		postprocess=_postprocess,
# 	)

@frappe.whitelist()
def make_out_subcontracting(source_name, target_doc=None):
    # Get total already subcontracted quantity
    total_subcontracted = frappe.db.sql("""
        SELECT COALESCE(SUM(total_quantity), 0)
        FROM `tabOut Subcontracting s`
        WHERE process_order = %s AND docstatus != 2
    """, (source_name,))[0][0]
    
    # Get Process Order total raw quantity
    process_order = frappe.get_doc("Process Order s", source_name)
    remaining_qty = flt(process_order.total_raw_qty) - flt(total_subcontracted)
    
    if remaining_qty <= 0:
        frappe.throw(_("All quantity has already been subcontracted. No remaining quantity available."))

    def _postprocess(source, target):
        target.process_order = source.name
        if not target.posting_date:
            target.posting_date = source.date
        
        # Set the remaining quantity as the default total
        target.total_quantity = remaining_qty
        
        # Calculate ratio for distributing qty to items
        original_total = flt(source.total_raw_qty)
        ratio = remaining_qty / original_total if original_total else 0

        for row in target.items or []:
            row.process_order_id = source.name
            # Adjust quantity based on remaining ratio
            original_qty = flt(row.quantity)
            row.quantity = original_qty * ratio
            # Recalculate amount based on new quantity
            row.amount = flt(row.quantity) * flt(row.rate)

    return get_mapped_doc( 
        "Process Order s", 
        source_name,
        {
            "Process Order s": {
                "doctype": "Out Subcontracting s",
                "field_map": {
                    "name": "process_order",
                    "date": "posting_date",
                },
            },
            "Process Order raw": {
                "doctype": "Out Subcontracting Item s",
                "field_map": {
                    "item_code": "item",
                    "item_name": "item_name",
                    "qty": "quantity",
                    "yeild": "yield",
                    "uom": "uom",
                    "rate": "rate",
                    "amount": "amount",
                    "batch": "batch_no",
                    "warehouse": "source_warehouse",
                },
            },
        },
        target_doc,
        postprocess=_postprocess,
    )


def get_completed_qty_from_batch_orders(process_order_name):
	if not process_order_name:
		return 0

	result = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(total_in_qty), 0)
		FROM `tabBatch Order s`
		WHERE docstatus < 2 AND process_order = %s
		""",
		(process_order_name,),
	)
	return flt(result[0][0]) if result else 0


def get_batch_order_qty_for_process(process_order_name, exclude_batch_order=None):
	if not process_order_name:
		return 0

	conditions = ["docstatus < 2", "process_order = %s"]
	values = [process_order_name]
	if exclude_batch_order:
		conditions.append("name != %s")
		values.append(exclude_batch_order)

	result = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(total_raw_qty), 0)
		FROM `tabBatch Order s`
		WHERE {" AND ".join(conditions)}
		""",
		tuple(values),
	)
	return flt(result[0][0]) if result else 0


@frappe.whitelist()
def get_remaining_batch_order_qty(process_order_name, exclude_batch_order=None):
	if not process_order_name:
		return 0

	process_order_qty = frappe.db.get_value("Process Order s", process_order_name, "total_raw_qty")
	used_qty = get_batch_order_qty_for_process(process_order_name, exclude_batch_order)
	return max(flt(process_order_qty) - flt(used_qty), 0)


def update_process_order_progress(process_order_name):
	if not process_order_name:
		return

	process_order = frappe.db.get_value(
		"Process Order s",
		process_order_name,
		["name", "total_in_qty"],
		as_dict=True,
	)
	if not process_order:
		return

	completed_qty = get_completed_qty_from_batch_orders(process_order_name)
	if process_order.total_in_qty:
		per_completed = min((completed_qty / process_order.total_in_qty) * 100, 100)
	else:
		per_completed = 0

	frappe.db.set_value(
		"Process Order s",
		process_order_name,
		"per_completed",
		flt(per_completed, 2),
		update_modified=False,
	)
