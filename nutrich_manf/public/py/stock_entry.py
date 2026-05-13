import json
from collections import defaultdict

import frappe
from frappe import _, bold 
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import (
	cint,
	comma_or,
	cstr,
	flt,
	format_time,
	formatdate,
	get_link_to_form,
	getdate,
	nowdate,
)

import erpnext
from erpnext.accounts.general_ledger import process_gl_map
from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.controllers.taxes_and_totals import init_landed_taxes_and_totals
from erpnext.manufacturing.doctype.bom.bom import (
	add_additional_cost,
	get_bom_items_as_dict,
	get_op_cost_from_sub_assemblies,
	# get_scrap_items_from_sub_assemblies,
	validate_bom_no,
)
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.batch.batch import get_batch_qty
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
	OpeningEntryAccountError,
)
from erpnext.stock.get_item_details import (
	get_barcode_data,
	get_bin_details,
	get_conversion_factor,
	get_default_cost_center, 
)
from erpnext.stock.serial_batch_bundle import (
	SerialBatchCreation,
	get_empty_batches_based_work_order,
	get_serial_or_batch_items,
)
from erpnext.stock.stock_ledger import NegativeStockError, get_previous_sle, get_valuation_rate
from erpnext.stock.utils import get_bin, get_incoming_rate

from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry


class FinishedGoodError(frappe.ValidationError):
	pass

class customStockEntry(StockEntry):

    def get_gl_entries(self, inventory_account_map):
        gl_entries = super().get_gl_entries(inventory_account_map)

        if not (self.purpose == "Manufacture" and self.custom_batch_order_id and self.value_difference):
            return gl_entries

        stock_adjustment_accounts = {d.expense_account for d in self.get("items") if d.expense_account}
        if not stock_adjustment_accounts:
            return gl_entries

        stock_in_hand_account = frappe.get_cached_value("Company", self.company, "default_inventory_account")
        if not stock_in_hand_account:
            return gl_entries

        filtered_gl_entries = []
        stock_in_hand_entry = None

        for entry in gl_entries:
            if entry.account in stock_adjustment_accounts:
                continue

            if entry.account == stock_in_hand_account:
                if not stock_in_hand_entry:
                    stock_in_hand_entry = entry
                continue

            filtered_gl_entries.append(entry)

        if stock_in_hand_entry:
            stock_in_hand_entry.debit = flt(self.value_difference) if self.value_difference > 0 else 0
            stock_in_hand_entry.credit = abs(flt(self.value_difference)) if self.value_difference < 0 else 0
            stock_in_hand_entry.debit_in_account_currency = stock_in_hand_entry.debit
            stock_in_hand_entry.credit_in_account_currency = stock_in_hand_entry.credit
            filtered_gl_entries.insert(0, stock_in_hand_entry)

        return filtered_gl_entries

    def validate_finished_goods(self):
        """
        1. Check if FG exists (mfg, repack)
        2. Check if Multiple FG Items are present (mfg)
        3. Check FG Item and Qty against WO if present (mfg)
        """
        production_item, wo_qty, finished_items = None, 0, []
        if self.work_order:
            wo_details = frappe.db.get_value("Work Order", self.work_order, ["production_item", "qty"])
            if wo_details:
                production_item, wo_qty = wo_details

        for d in self.get("items"):
            if d.is_finished_item:
                if not self.work_order:
                    # Independent MFG Entry/ Repack Entry, no WO to match against
                    finished_items.append(d.item_code)
                    continue

                if d.item_code != production_item:
                    frappe.throw(
                        _("Finished Item {0} does not match with Work Order {1}").format(
                            d.item_code, self.work_order
                        )
                    )
                elif flt(d.transfer_qty) > flt(self.fg_completed_qty):
                    frappe.throw(
                        _("Quantity in row {0} ({1}) must be same as manufactured quantity {2}").format(
                            d.idx, d.transfer_qty, self.fg_completed_qty
                        )
                    )

                finished_items.append(d.item_code)

        if not finished_items:
            frappe.throw(
                msg=_("There must be atleast 1 Finished Good in this Stock Entry").format(self.name),
                title=_("Missing Finished Good"),
                exc=FinishedGoodError,
            )

        if self.purpose == "Manufacture":
            if len(set(finished_items)) > 100:
                frappe.throw(
                    msg=_("Multiple items cannot be marked as finished item"),
                    title=_("Note"),
                    exc=FinishedGoodError,
                )

            allowance_percentage = flt(
                frappe.db.get_single_value(
                    "Manufacturing Settings", "overproduction_percentage_for_work_order"
                )
            )
            allowed_qty = wo_qty + ((allowance_percentage / 100) * wo_qty)

            # No work order could mean independent Manufacture entry, if so skip validation
            if self.work_order and self.fg_completed_qty > allowed_qty:
                frappe.throw(
                    _("For quantity {0} should not be greater than allowed quantity {1}").format(
                        flt(self.fg_completed_qty), allowed_qty
                    )
                )


@frappe.whitelist()
def calculate_difference(doc,method=None):
    diff_qty1 = 0
    diff_qty2 = 0
    for row in doc.items:
        if not row.is_finished_item and not row.is_legacy_scrap_item:
            diff_qty1 += row.qty
        if row.is_finished_item == 1 or row.is_legacy_scrap_item == 1:
            diff_qty2 += row.qty 
    doc.custom_difference_qty_nutrich = diff_qty1 - diff_qty2


@frappe.whitelist()
def set_cost_center(doc, method=None):
    if doc.cost_center:
        for row in doc.items:
            row.cost_center = doc.cost_center
