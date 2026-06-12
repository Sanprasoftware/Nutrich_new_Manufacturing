frappe.ui.form.on('Purchase Order', {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }
        frm.add_custom_button('Create Gate Pass', () => {
            create_gate_pass_from_reference(frm);
        });
        frm.add_custom_button("Mail To Supplier", () => {
            frm.call({
                method: "nutrich_manf.public.py.purchase_order.send_mail_to_supplier",
                args: {
                    docname: frm.doc.name
                },
                callback: (r) => {
                    if (r.message) {
                        frappe.msgprint("Mail sent to supplier successfully.");
                    } else {
                        frappe.msgprint("Failed to send mail to supplier.");
                    }
                }
            })
        });
        frm.add_custom_button("Mail To Broker", () => {
            frm.call({
                method: "nutrich_manf.public.py.purchase_order.send_mail_to_broker",
                args: {
                    docname: frm.doc.name
                },
                callback: (r) => {
                    if (r.message) {
                        frappe.msgprint("Mail sent to supplier successfully.");
                    } else {
                        frappe.msgprint("Failed to send mail to supplier.");
                    }
                }
            })
        })
    }
});

function create_gate_pass_from_reference(frm) { 
    frappe.call({
        method: 'nutrich_manf.nutrich_manf.doctype.gate_pass_s.gate_pass_s.get_gate_pass_payload',
        args: {
            reference_doctype: frm.doctype,
            reference: frm.doc.name
        },
        callback: (r) => {
            const payload = r.message || {};
            const items = payload.items || [];

            frappe.model.with_doctype('Gate Pass s', () => {
                const doc = frappe.model.get_new_doc('Gate Pass s');
                doc.reference_doctype = payload.reference_doctype;
                doc.reference = payload.reference;

                doc.gate_pass_items = [];
                items.forEach((row) => {
                    const child = frappe.model.add_child(doc, 'Gate Pass Items s', 'gate_pass_items');
                    child.item_code = row.item_code || '';
                    child.item_name = row.item_name || '';
                    child.quantity = row.quantity || 0;
                    child.uom = row.uom || '';
                });

                frappe.set_route('Form', 'Gate Pass s', doc.name);
            });
        }
    });
}
