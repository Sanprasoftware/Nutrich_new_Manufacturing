// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

frappe.ui.form.on("In Subcontracting s", {
	refresh(frm) {

	},
    onload(frm) {
		frm.set_query("batch_no", "in_raw_material", function(doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            if (!row.item) {
              return { filters: { name: "" } }; // no item selected
            }
            return {    
              filters: {
                item: row.item
              }
            };
        });
		
        frm.set_query("batch", "finish_items", function(doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            if (!row.item_code) {
              return { filters: { name: "" } }; // no item selected
            }
            return {    
              filters: {
                item: row.item_code
              }
            };
        });
    }
});
  


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
});
  
