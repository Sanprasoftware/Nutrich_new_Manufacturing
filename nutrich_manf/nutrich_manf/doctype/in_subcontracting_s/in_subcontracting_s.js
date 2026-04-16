// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

// frappe.ui.form.on("In Subcontracting s", {
// 	refresh(frm) {

// 	},
// });
  


frappe.ui.form.on("In Subcontracting Item s", {
	rate(frm) {
        frappe.call({
            method: "calculate_finished_items_calculate_totals",
            doc: frm.doc,
            callback: function(r){
                console.log(r)
                frm.refresh_fields(["finished_items"]);     
            }
        })
	},
	qty(frm) {
        frappe.call({
            method: "calculate_finished_items_calculate_totals",
            doc: frm.doc,
            callback: function(r){
                console.log(r)
                frm.refresh_fields(["finished_items"]);     
            }
        })
	},
    finished_items_add(frm,cdt,cdn){
        frappe.model.set_value(cdt,cdn,"ref_challan",frm.doc.out_subcontracting_id)
        frm.refresh_fields(["finished_items"]); 
    }
});
  