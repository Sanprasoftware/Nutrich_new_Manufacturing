frappe.ui.form.on("Process Definition s", {
    refresh(frm) {
        if (frm.is_new()) return;

        frm.make_methods = frm.make_methods || {};
        frm.make_methods["Process Order s"] = () => {
            frappe.model.open_mapped_doc({
                method:
                    "nutrich_manf.nutrich_manf.doctype.process_definition_s.process_definition_s.make_process_order",
                frm: frm,
            }); 
        };

        frm.add_custom_button("Create Process Order", () => {
            frm.make_methods["Process Order s"](); 
        });
    },
});

frappe.ui.form.on("Process Definition raw", {
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



frappe.ui.form.on("Process Definition Cost", {
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




frappe.ui.form.on("Process Definition Finish", {
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
    },
    process_definition_finish_delete(frm,cdt,cdn){
        calculateAmt_definition_finish(frm)   
    },
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

   


frappe.ui.form.on("Process Definition Scrap", {
    yeild(frm,cdt,cdn){
        calculateAmt_scrap(frm)  
    },
    item_code(frm,cdt,cdn){
        calculateAmt_scrap(frm)  
    },
    rate(frm,cdt,cdn){
        calculateAmt_scrap(frm)  
    },
    warehouse(frm,cdt,cdn){
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
