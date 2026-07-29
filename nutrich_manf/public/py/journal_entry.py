import frappe
from frappe import _
from frappe.utils import flt


def validate_cost_center_balance(doc, method=None):
    cost_center_totals = {}

    for row in doc.accounts:
        if not row.cost_center:
            continue

        if row.cost_center not in cost_center_totals:
            cost_center_totals[row.cost_center] = {
                "debit": 0.0,
                "credit": 0.0,
            }

        cost_center_totals[row.cost_center]["debit"] += flt(row.debit)
        cost_center_totals[row.cost_center]["credit"] += flt(row.credit)

    errors = []

    for cost_center, values in cost_center_totals.items():
        if flt(values["debit"], 2) != flt(values["credit"], 2):
            errors.append(
                _(
                    "<b>{0}</b> → Debit: {1}, Credit: {2}"
                ).format(
                    cost_center,
                    values["debit"],
                    values["credit"]
                )
            )

    if errors:
        frappe.throw(
            _("The following Cost Centers are not balanced:<br><br>{0}").format(
                "<br>".join(errors)
            )
        )