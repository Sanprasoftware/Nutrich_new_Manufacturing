frappe.ui.form.on('Delivery Note', {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }
        frm.add_custom_button('Create Gate Pass', () => {
            create_gate_pass_from_reference(frm);
        });
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
