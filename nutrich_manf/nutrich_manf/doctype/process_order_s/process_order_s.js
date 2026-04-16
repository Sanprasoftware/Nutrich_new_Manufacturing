frappe.ui.form.on("Process Order s", {
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

        //Create Batch Order Button + Connection "+" Code
        if (frm.is_new()) return;
        frm.make_methods = frm.make_methods || {};
        frm.make_methods["Batch Order s"] = () => { 
            frappe.model.open_mapped_doc({
                method:
                    "nutrich_manf.nutrich_manf.doctype.process_order_s.process_order_s.make_batch_order",
                frm: frm,
            });
        };
        frm.add_custom_button("Batch Order", () => {
            frm.make_methods["Batch Order s"]();
        }, __("Create")); 
        


        // Create Gate Pass Button + Connection "+" Code
        frm.make_methods["Gate Pass s"] = () => {
            frappe.model.open_mapped_doc({
                method:
                    "nutrich_manf.nutrich_manf.doctype.gate_pass_s.gate_pass_s.make_gate_pass",
                frm: frm,
                args: {
                    reference_doctype: frm.doctype,
                },
            });
        };
        frm.add_custom_button("Gate Pass", () => {
            frm.make_methods["Gate Pass s"]();
        }, __("Create"));

        
        // Create Out Subcontracting Button + Connection "+" Code
        frm.make_methods["Out Subcontracting s"] = () => {
            frappe.model.open_mapped_doc({
                method:
                    "nutrich_manf.nutrich_manf.doctype.process_order_s.process_order_s.make_out_subcontracting",
                frm: frm,
            });
        };
        frm.add_custom_button("Out Subcontracting", () => {
            frm.make_methods["Out Subcontracting s"]();
        }, __("Create"));
    },
    
    onload(frm) {
      frm.set_query("batch", "process_definition_raw", function(doc, cdt, cdn) {
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

      frm.set_query("batch", "process_definition_finish", function(doc, cdt, cdn) {
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

        frm.set_query("batch", "process_definition_scrap", function(doc, cdt, cdn) {
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



frappe.ui.form.on("Process Order raw", {
    qty(frm,cdt,cdn){
        calculateAmt(frm)  
    },
    rate(frm,cdt,cdn){
        calculateAmt(frm)  
    },
    item_code(frm,cdt,cdn){
        // const row = locals[cdt][cdn];
        // row.batch = "";
        // frm.refresh_field("process_definition_raw");
        calculateAmt(frm)  
    }, 
    process_type(frm,cdt,cdn){
        calculateAmt(frm)  
    },
    process_definition_raw_delete(frm,cdt,cdn){
        calculateAmt(frm)  
    },

    batch(frm, cdt, cdn) {
      const row = locals[cdt][cdn];

      if (!row.batch || !row.item_code) {
        return;
      }

      frappe.db.get_value(
        "Batch",
        { name: row.batch, item: row.item_code },
        "name"
      ).then((r) => {
        if (!r || !r.message || !r.message.name) {
          row.batch = "";
          frm.refresh_field("process_definition_raw");
          frappe.msgprint(
            __("Batch {0} is not valid for item {1}.", [row.batch, row.item_code])
          );
        }
      });
    },
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



frappe.ui.form.on("Process Order Cost", {
    per_kg_cost(frm,cdt,cdn){
        calculate_cost(frm)  
    },
    process_definition_cost_delete(frm,cdt,cdn){
        calculate_cost(frm)  
    },
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




frappe.ui.form.on("Process Order Finish", {
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

   


frappe.ui.form.on("Process Order Scrap", {
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
