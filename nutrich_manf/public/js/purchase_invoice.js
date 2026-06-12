frappe.ui.form.on('Purchase Invoice', {
    custom_is_rate: function (frm,cdt,cdn) {
		frm.doc.custom_is_qty = 0;
		frm.refresh_field("custom_is_qty");
    },

    custom_is_qty: function (frm,cdt,cdn) {
		frm.doc.custom_is_rate = 0;
		frm.refresh_field("custom_is_rate");
    }
});
