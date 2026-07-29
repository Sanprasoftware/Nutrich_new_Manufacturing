frappe.ui.form.on('Purchase Invoice', {
    custom_is_rate: function (frm,cdt,cdn) {
      frm.doc.custom_is_qty = 0;
      frm.refresh_field("custom_is_qty");
    },

    custom_is_qty: function (frm,cdt,cdn) {
      frm.doc.custom_is_rate = 0;
      frm.refresh_field("custom_is_rate");
    },
    refresh: function (frm) {
      if (frm.doc.apply_tds && frm.doc.supplier){
        frappe.db.get_value("Supplier", frm.doc.supplier, "tax_withholding_category").then((r) => {
          if (r.message){
            console.log(r.message)
            frm.set_value(
              "custom_tax_withholding_category",
              r.message.tax_withholding_category
            );
          }
        });
      } else if (!frm.doc.apply_tds) {
        frm.set_value("custom_tax_withholding_category", "")
      }
    }
});
