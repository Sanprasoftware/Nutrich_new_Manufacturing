// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gate Pass s', {
    setup(frm) {
        frm.set_query('reference_doctype', () => {
            return {
                filters: [
                    ['DocType', 'name', 'in', [
                        'Delivery Note',
                        'Purchase Order',
                        'Sales Invoice',
                        'Stock Entry',
                        'Process Order s'
                    ]]
                ]
            };
        });
        frm.set_query('party_type', () => {
            return {
                filters: [
                    ['DocType', 'name', 'in', ['Customer', 'Supplier']]
                ]
            };
        });
    },
    reference(frm) {
        if (!frm.doc.reference_doctype || !frm.doc.reference) {
            return;
        }

        frm.call({
            method: 'get_reference_items',
            args: {
                reference_doctype: frm.doc.reference_doctype,
                reference: frm.doc.reference
            },
            callback: (r) => {
                const rows = r.message || [];
                if (!rows.length) {
                    return;
                }

                frm.clear_table('gate_pass_items');

                rows.forEach((row) => {
                    const child = frm.add_child('gate_pass_items');
                    child.item_code = row.item_code || '';
                    child.item_name = row.item_name || '';
                    child.quantity = row.quantity || 0;
                    child.uom = row.uom || '';
                });

                frm.refresh_field('gate_pass_items');
            }
        });
    }
});
