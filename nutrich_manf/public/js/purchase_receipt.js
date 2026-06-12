frappe.ui.form.on("Purchase Receipt Item", {
    custom_vehicle_emty_weight_mt(frm,cdt, cdn) {
        calculate_weight_details(frm, cdt, cdn);
    },
    custom_vehicle_loaded_weight_mt(frm,cdt, cdn) {
        calculate_weight_details(frm, cdt, cdn);
    },
    custom_no_of_packaging(frm,cdt, cdn) {
        calculate_weight_details(frm, cdt, cdn);
    },
    custom_weight_for_payment(frm,cdt, cdn) {
        calculate_weight_details(frm, cdt, cdn);
    },
    custom_packaging_weight(frm,cdt, cdn) {
        calculate_weight_details(frm, cdt, cdn);
    },
    custom_payment_weight(frm,cdt, cdn) {
        calculate_weight_details(frm, cdt, cdn);
    },
    custom_gross_weight(frm,cdt, cdn) {
        calculate_weight_details(frm, cdt, cdn);
    },
    received_qty(frm,cdt, cdn) {
        calculate_weight_details(frm, cdt, cdn);
    },
})

function calculate_weight_details(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.custom_vehicle_emty_weight_mt && row.custom_vehicle_loaded_weight_mt){
        row.custom_gross_weight = row.custom_vehicle_loaded_weight_mt - row.custom_vehicle_emty_weight_mt;
    }

    if (row.received_qty < row.custom_gross_weight){
        row.custom_accepted_weight = row.received_qty;
    }

    if (row.custom_packaging_weight >=0 && row.custom_accepted_weight >=0){
        row.custom_net_weight = row.custom_accepted_weight - row.custom_packaging_weight;
    }
    // row.custom_packaging_weight = row.custom_accepted_weight - row.custom_packaging_weight;
    
    
    if (row.custom_weight_for_payment ==  "Gross for Net"){
        row.custom_payment_weight = row.custom_accepted_weight
    }else {
        row.custom_payment_weight = row.custom_net_weight
    }

    if (row.custom_payment_weight){
        row.custom_shortage = row.received_qty - row.custom_payment_weight;
    }

    frm.refresh_field("items");
}