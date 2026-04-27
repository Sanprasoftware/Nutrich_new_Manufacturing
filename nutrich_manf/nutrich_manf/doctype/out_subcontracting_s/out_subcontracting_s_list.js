frappe.listview_settings["Out Subcontracting s"] = {
	add_fields: ["per_received", "total_quantity"],

	formatters: {
		per_received(value) {
			const percent = Math.max(0, Math.min(flt(value || 0), 100));
			const color =
				percent >= 100 ? "#1f7a3e" : percent >= 60 ? "#b7791f" : "#c53030";

			return `
				<div style="min-width: 130px;">
					<div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
						<span>Progress</span>
						<span>${frappe.format(percent, { fieldtype: "Percent", precision: 2 })}</span>
					</div>
					<div style="height:8px; background:#e5e7eb; border-radius:999px; overflow:hidden;">
						<div style="width:${percent}%; height:100%; background:${color}; border-radius:999px;"></div>
					</div>
				</div>
			`;
		},
	},
};
