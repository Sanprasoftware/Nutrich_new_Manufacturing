// Copyright (c) 2026, Sanpra and contributors
// For license information, please see license.txt

frappe.ui.form.on("Out Subcontracting s", {
	supplier(frm) {
		if (!frm.doc.supplier) {
			frm.set_value("supplier_address", "");
			frm.set_value("supplier_address_texteditor", "");
			frm.set_value("supplier_address_gstin", "");
			frm.set_value("company_address", "");
			frm.set_value("company_address_texteditor", "");
			frm.set_value("company_address_gstin", "");
			return;
		}
 
		set_supplier_gstin_from_default_address(frm);

		if (!frm.doc.company) {
			return;
		}

		frappe.call({
			method: "erpnext.accounts.party.get_party_details",
			args: {
				party: frm.doc.supplier,
				party_type: "Supplier",
				company: frm.doc.company,
				posting_date: frm.doc.posting_date || frappe.datetime.get_today(),
				doctype: frm.doc.doctype,
			},
			callback: function (r) {
				const details = r.message || {};

				if (details.supplier_address) {
					frm.set_value("supplier_address", details.supplier_address);
					set_supplier_address_display_and_gstin(frm);
				}

				if (details.address_display) {
					frm.set_value("supplier_address_texteditor", details.address_display);
				}

				if (details.company_address) {
					frm.set_value("company_address", details.company_address);
					set_company_address_display_and_gstin(frm);
				}

				if (details.company_address_display) {
					frm.set_value("company_address_texteditor", details.company_address_display);
				}

				if (details.tax_category) {
					frm.set_value("gst_category", details.tax_category);
				}
			}, 
		});
	}, 
	supplier_address(frm) {
		set_supplier_address_display_and_gstin(frm);
	},
	company_address(frm) {
		set_company_address_display_and_gstin(frm);
	},
 
});

function set_supplier_address_display_and_gstin(frm) {
	if (!frm.doc.supplier_address) {
		frm.set_value("supplier_address_texteditor", "");
		frm.set_value("supplier_address_gstin", "");
		set_supplier_gstin_from_default_address(frm);
		return;
	}

	frappe.call({
		method: "frappe.contacts.doctype.address.address.get_address_display",
		args: { address_dict: frm.doc.supplier_address },
		callback: function (r) {
			if (r.message) {
				frm.set_value("supplier_address_texteditor", r.message);
			}
		},
	});

	if (frappe.meta.get_docfield("Address", "gstin")) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Address",
				filters: { name: frm.doc.supplier_address },
				fieldname: ["gstin"],
			},
			callback: function (r) {
				if (r.message && r.message.gstin) {
					frm.set_value("supplier_address_gstin", r.message.gstin);
				} else {
					frm.set_value("supplier_address_gstin", "");
					set_supplier_gstin_from_default_address(frm);
				}
			},
		});
	} else {
		frm.set_value("supplier_address_gstin", "");
		set_supplier_gstin_from_default_address(frm);
	}
}

function set_company_address_display_and_gstin(frm) {
	if (!frm.doc.company_address) {
		frm.set_value("company_address_texteditor", "");
		frm.set_value("company_address_gstin", "");
		return;
	}

	frappe.call({
		method: "frappe.contacts.doctype.address.address.get_address_display",
		args: { address_dict: frm.doc.company_address },
		callback: function (r) {
			if (r.message) {
				frm.set_value("company_address_texteditor", r.message);
			}
		},
	});

	if (frappe.meta.get_docfield("Address", "gstin")) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Address",
				filters: { name: frm.doc.company_address },
				fieldname: ["gstin"],
			},
			callback: function (r) {
				if (r.message && r.message.gstin) {
					frm.set_value("company_address_gstin", r.message.gstin);
				} else {
					frm.set_value("company_address_gstin", "");
				}
			},
		});
	} else {
		frm.set_value("company_address_gstin", "");
	}
}

function set_supplier_gstin_from_default_address(frm) {
	if (frm.doc.supplier_address_gstin) {
		return;
	}

	if (!frm.doc.supplier) {
		frm.set_value("supplier_address_gstin", "");
		return;
	}

	if (!frappe.meta.get_docfield("Address", "gstin")) {
		return;
	}

	frappe.call({
		method: "frappe.contacts.doctype.address.address.get_default_address",
		args: {
			doctype: "Supplier",
			name: frm.doc.supplier,
		},
		callback: function (r) {
			const address_name = r.message;
			if (!address_name) {
				frm.set_value("supplier_address_gstin", "");
				return;
			}

			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Address",
					filters: { name: address_name },
					fieldname: ["gstin"],
				},
				callback: function (r2) {
					if (r2.message && r2.message.gstin) {
						frm.set_value("supplier_address_gstin", r2.message.gstin);
					} else {
						frm.set_value("supplier_address_gstin", "");
					}
				},
			});
		},
	});
}

 
