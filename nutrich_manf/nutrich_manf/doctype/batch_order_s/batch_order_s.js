frappe.ui.form.on("Batch Order s", {
    update_qty(frm){
        frappe.call({
            method: "update_qty_button",
            doc: frm.doc,
            callback: function(r){
                console.log(r)
                frm.refresh_fields();
            }
        }) 
    },  
    refresh(frm) {
        if (frm.is_new()) return;

        frm.make_methods = frm.make_methods || {};
        frm.make_methods["Stock Entry"] = () => {
            frappe.model.open_mapped_doc({
                method:
                    "nutrich_manf.nutrich_manf.doctype.batch_order_s.batch_order_s.make_stock_entry",
                frm: frm,
            }); 
        };
 
        frappe.call({
            method: "nutrich_manf.nutrich_manf.doctype.batch_order_s.batch_order_s.get_remaining_stock_entry_raw_qty",
            args: {
                batch_order_name: frm.doc.name,
            },
            callback: function(r) {
                if (parseFloat(r.message || 0) > 0) {
                    frm.add_custom_button("Create Stock Entry", () => {
                        frm.make_methods["Stock Entry"]();
                    });
                }
            }
        });

        frm.add_custom_button("Update Cost", () => {
            console.log("Button Clicked");
            frm.call({
                method: "update_cost",
                doc: frm.doc,
                callback: function(r){
                    console.log(r)
                    frm.refresh_fields();
                }
            }) 
        });

        if (frm.doc.docstatus === 1) {
            frm.add_custom_button("In Subcontracting", () => {
                frm.call({
                    method: "create_in_subcontracting",
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message) {
                            let doc = frappe.model.sync(r.message)[0];
                            frappe.set_route("Form", doc.doctype, doc.name);
                        }
                    }
                });
            });
        }
    },
    onload(frm) {
        set_non_group_warehouse_queries(frm);
        //   frm.set_query("batch", "process_definition_raw", function(doc, cdt, cdn) {
        //     const row = locals[cdt][cdn];
        //     if (!row.item_code) {
        //       return { filters: { name: "" } }; // no item selected
        //     }
        //     return {
        //       filters: {
        //         item: row.item_code
        //       }
        //     };
        //   }); 
        
        frm.set_query("batch", "process_definition_raw", function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];

            return {
                query: "erpnext.controllers.queries.get_batch_no",
                filters: {
                    item_code: row.item_code,
                    warehouse: row.warehouse,
                    posting_date: doc.date
                }
            };
        });

        // frm.set_query("batch", "process_definition_finish", function(doc, cdt, cdn) {
        //     const row = locals[cdt][cdn];
        //     if (!row.item_code) {
        //       return { filters: { name: "" } }; // no item selected
        //     }
        //     return {    
        //       filters: {
        //         item: row.item_code
        //       }
        //     };
        // });

        frm.set_query("batch", "process_definition_finish", function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];

            return {
                query: "erpnext.controllers.queries.get_batch_no",
                filters: {
                    item_code: row.item_code,
                    warehouse: row.warehouse,
                    posting_date: doc.date
                }
            };
        });

        // frm.set_query("batch", "process_definition_scrap", function(doc, cdt, cdn) {
        //     const row = locals[cdt][cdn];
        //     if (!row.item_code) {
        //     return { filters: { name: "" } }; // no item selected
        //     }   
        //     return {
        //     filters: {
        //         item: row.item_code
        //     }
        //     };
        // });
           
        frm.set_query("batch", "process_definition_scrap", function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];

            return {
                query: "erpnext.controllers.queries.get_batch_no",
                filters: {
                    item_code: row.item_code,
                    warehouse: row.warehouse,
                    posting_date: doc.date
                }
            };
        });
      
    }
});

function set_non_group_warehouse_queries(frm) {
    [
        "process_definition_raw",
        "process_definition_finish",
        "process_definition_scrap"
    ].forEach((table_field) => {
        frm.set_query("warehouse", table_field, () => {
            return {
                filters: {
                    is_group: 0
                }
            };
        });
    });
}


frappe.ui.form.on("Process Batch raw", {
    qty(frm,cdt,cdn){
        calculateAmt(frm)  
    },
    rate(frm,cdt,cdn){
        calculateAmt(frm)  
    },
    item_code(frm,cdt,cdn){
        calculateAmt(frm)  
    },
    process_type(frm,cdt,cdn){
        calculateAmt(frm)  
    },
    process_definition_raw_delete(frm,cdt,cdn){
        calculateAmt(frm)  
    }
});
function calculateAmt(frm){
    frappe.call({
        method: "process_defination_raw_amount",
        doc: frm.doc,
        callback: function(r){
            console.log(r)
            frm.refresh_fields(["total_raw_qty"]);
        }
    })
}



frappe.ui.form.on("Process Batch Cost", {
    per_kg_cost(frm,cdt,cdn){
        calculate_cost(frm)  
    },
    process_definition_cost_delete(frm,cdt,cdn){
        calculate_cost(frm)  
    },
    cost(frm,cdt,cdn){
        frappe.call({
            method: "update_per_kg_cost",
            doc: frm.doc,
            callback: function(r){
                console.log(r)
                frm.refresh_fields(["per_kg_cost"]);
            }
        })  
    }
});

function calculate_cost(frm){
    frappe.call({
        method: "calculatate_cost",
        doc: frm.doc,
        callback: function(r){
            console.log(r)
            frm.refresh_fields(["total_cost"]);
        }
    })
}




frappe.ui.form.on("Process Batch Finish", {
    item_code(frm,cdt,cdn){
        calculateAmt_definition_finish(frm)  
    },
    yeild(frm,cdt,cdn){
        calculateAmt_definition_finish(frm)  
    },
    warehouse(frm,cdt,cdn){
        calculateAmt_definition_finish(frm)   
    },
    process_definition_finish(frm,cdt,cdn){
        calculateAmt_definition_finish(frm)   
    }
});
function calculateAmt_definition_finish(frm){
    frappe.call({
        method: "process_definition_finish_amount",
        doc: frm.doc,
        callback: function(r){
            console.log(r)
            // frm.refresh_fields(["amount"]);
            frm.refresh_fields(["amount","total_raw_qty"]);
        }
    })
}

   


frappe.ui.form.on("Process Batch Scrap", {
    yeild(frm,cdt,cdn){
        calculateAmt_scrap(frm)  
    },
    item_code(frm,cdt,cdn){
        calculateAmt_scrap(frm)   
    },
    rate(frm,cdt,cdn){
        calculateAmt_scrap(frm)  
    },
    process_definition_scrap_delete(frm,cdt,cdn){
        calculateAmt_scrap(frm)  
    },
});
function calculateAmt_scrap(frm){
    frappe.call({
        method: "calculate_process_definition_scrap_amount",
        doc: frm.doc,
        callback: function(r){
            console.log(r)
            frm.refresh_fields(["amount","total_raw_qty"]);
        }
    })
}
