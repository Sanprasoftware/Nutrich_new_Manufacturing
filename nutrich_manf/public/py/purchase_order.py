import frappe

@frappe.whitelist()
def send_mail_to_supplier(docname):
    po = frappe.get_doc("Purchase Order", docname)

    supplier_email = frappe.db.get_value(
        "Supplier",
        po.supplier,
        "email_id"
    )

    if not supplier_email:
        frappe.throw(f"Email ID not found for Supplier {po.supplier}")

    items = ""

    for item in po.items:
        items += f"""
        <tr>
            <td>{item.item_name}</td>
            <td>{item.qty}</td>
            <td>{item.rate}</td>
            <td>{item.amount}</td>
        </tr>
        """

    message = f"""
    <p>Dear {po.supplier},</p>

    <p>
    Please find attached Purchase Order No. <b>{po.name}</b>
    dated <b>{po.transaction_date}</b>.
    </p>

    <h4>PO Summary</h4>

    <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th>Item</th>
            <th>Qty</th>
            <th>Rate</th>
            <th>Amount</th>
        </tr>
        {items}
    </table>

    <br>

    <p>
    Delivery Address: {po.shipping_address or ""}
    </p>

    <p>
    Kindly acknowledge receipt of this PO and confirm delivery schedule.
    </p>

    <br>

    <p>
    Best Regards,<br>
    {frappe.session.user}
    </p>
    """

    frappe.sendmail(
        recipients=[supplier_email],
        subject=f"Purchase Order No. {po.name}",
        message=message,
        reference_doctype="Purchase Order",
        reference_name=po.name,
        now=True
    )

    return True



@frappe.whitelist()
def send_mail_to_broker(docname):
    po = frappe.get_doc("Purchase Order", docname)

    broker_email = po.custom_broker_email  # Change field name as required

    if not broker_email:
        frappe.throw("Broker Email is not specified.")

    message = f"""
    <p>Dear {po.broker_name or 'Broker Name'},</p>

    <p>
    We have issued Purchase Order No. <b>{po.name}</b> dated <b>{po.transaction_date}</b>
    to <b>{po.supplier}</b> for
    {', '.join([f"{d.item_name} ({d.qty})" for d in po.items])}.
    PO is attached for your reference.
    All terms and condition as per PO.
    </p>

    <p>
    <b>Delivery Address:</b> {po.shipping_address or ''}
    </p>

    <p>Request your support for:</p>

    <ol>
        <li>Getting PO acknowledgment + confirmed production/despatch schedule from supplier</li>
        <li>Coordinating Dispatch quantity and before delivery period</li>
        <li>Updating us immediately on any delay, quality, or compliance issues</li>
    </ol>

    <p>
    <b>Order details:</b> Rs. {po.grand_total},
    Delivery at {po.shipping_address_name or ''} by {po.schedule_date or ''}
    </p>

    <p>
    Please confirm once supplier acknowledges the PO duly seal and signed by supplier.
    </p>

    <p>
    Thanks,<br>
    {frappe.session.user}
    </p>
    """

    attachments = [
        frappe.attach_print(
            "Purchase Order",
            po.name,
            file_name=po.name,
            print_format="Standard"
        )
    ]

    frappe.sendmail(
        recipients=[broker_email],
        subject=f"PO No. {po.name} issued to {po.supplier} - Request follow-up",
        message=message,
        attachments=attachments,
        now=True
    )

    return True



import frappe
from frappe.utils import getdate, nowdate


def send_pending_delivery_reminders():
    today = getdate(nowdate())

    purchase_orders = frappe.get_all(
        "Purchase Order",
        filters={"docstatus": 1},
        fields=["name"]
    )

    for po_row in purchase_orders:
        po = frappe.get_doc("Purchase Order", po_row.name)

        total_ordered_qty = 0
        total_received_qty = 0
        total_pending_qty = 0
        item_names = []
        delivery_date = None

        for item in po.items:

            received_qty = frappe.db.sql("""
                SELECT COALESCE(SUM(pri.qty), 0)
                FROM `tabPurchase Receipt Item` pri
                INNER JOIN `tabPurchase Receipt` pr
                    ON pr.name = pri.parent
                WHERE pr.docstatus = 1
                AND pri.purchase_order = %s
                AND pri.po_detail = %s
            """, (po.name, item.name))[0][0] or 0

            pending_qty = item.qty - received_qty

            total_ordered_qty += item.qty
            total_received_qty += received_qty

            if pending_qty <= 0:
                continue

            total_pending_qty += pending_qty

            item_names.append(
                f"{item.item_name} (Pending: {pending_qty})"
            )

            if item.schedule_date:
                item_days_left = (getdate(item.schedule_date) - today).days

                if item_days_left in [7, 5, 2]:
                    delivery_date = item.schedule_date

        # No pending quantity
        if total_pending_qty <= 0:
            continue

        # No item matching 7/5/2 day condition
        if not delivery_date:
            continue

        days_left = (getdate(delivery_date) - today).days

        item_list = ", ".join(item_names)

        # =====================================================
        # SUPPLIER EMAIL
        # =====================================================

        supplier_email = frappe.db.get_value(
            "Supplier",
            po.supplier,
            "email_id"
        )

        if supplier_email:

            supplier_message = f"""
            <p>Dear {po.supplier}/Team,</p>

            <p>
            Gentle reminder regarding pending delivery against Purchase Order No. {po.name}
            dated {po.transaction_date} for {item_list}.
            </p>

            <p><b>Status Update:</b></p>

            <ul>
                <li>Total Ordered: {total_ordered_qty}</li>
                <li>Delivered Till Date: {total_received_qty}</li>
                <li>Pending Qty: {total_pending_qty}</li>
                <li>Committed Delivery Date: {delivery_date}</li>
                <li>Days Remaining: {days_left}</li>
            </ul>

            <p>
            We have not received the balance quantity yet.
            This delay is impacting our production/sales schedule.
            </p>

            <p>
            Please confirm the exact despatch date for the pending quantity by EOD today.
            Share dispatch details if material is already dispatched.
            </p>

            <p>
            We value our partnership and request your urgent attention to close this pending delivery.
            Contact us for any query xxxx.
            </p>

            <p>
            Best regards,<br>
            Purchase Department
            </p>
            """

            frappe.sendmail(
                recipients=[supplier_email],
                subject=f"Reminder: Pending Delivery of {total_pending_qty} Units Against PO No. {po.name}",
                message=supplier_message,
                reference_doctype="Purchase Order",
                reference_name=po.name,
                now=True
            )

        # =====================================================
        # BROKER EMAIL
        # =====================================================

        broker_email = po.custom_broker_email

        if broker_email:

            broker_message = f"""
            <p>Dear {po.custom_broker_name or 'Broker Name'},</p>

            <p>
            This is a reminder for the pending delivery against PO No. {po.name}
            placed with {po.supplier} for {item_list}.
            PO date: {po.transaction_date}.
            </p>

            <p><b>Current Status:</b></p>

            <ul>
                <li>Pending Qty: {total_pending_qty} units</li>
                <li>Original Delivery Date: {delivery_date}</li>
                <li>Status: Delivery Due in {days_left} days</li>
            </ul>

            <p>
            Request you to urgently follow up with the supplier and:
            </p>

            <ol>
                <li>Get a firm commitment date for balance delivery</li>
                <li>Share reason for delay + revised ETD</li>
                <li>Ensure priority handling to avoid further demurrage/penalty at our end</li>
            </ol>

            <p>
            Please revert with supplier's written confirmation by today.
            </p>

            <p>
            Appreciate your quick support.
            </p>

            <p>
            Best regards,<br>
            Purchase Department
            </p>
            """

            frappe.sendmail(
                recipients=[broker_email],
                subject=f"Reminder: Expedite Pending Qty for PO No. {po.name} with {po.supplier}",
                message=broker_message,
                reference_doctype="Purchase Order",
                reference_name=po.name,
                now=True
            )