import frappe

def validate_cf_agent(doc):
    """
    Validate the Clearing and Forwarding Agent
    """
    if doc.c_and_f_company and doc.clearing_agent:
        cf_company = frappe.get_cached_value("Clearing Agent", doc.clearing_agent, "c_and_f_company")
        if doc.c_and_f_company != cf_company:
            frappe.throw(f"The selected Clearing Agent: <b>{doc.clearing_agent}</b> does not belong to the selected Clearing and Forwarding Company: <b>{self.c_and_f_company}</b>")

def validate_draft_doc(doctype, docname):
    """
    Validate linking of draft documents
    """
    if frappe.db.get_value(doctype, docname, "docstatus") == 0:
        frappe.throw(f"Cannot link a draft document: <b>{doctype}- {docname}</b><br>Kindly submit the document first.")

def validate_qty_storage_item(doc):
    """
    Validate the quantity of storage item if it matches the number of container child references.
    If the quantity does not match, it will adjust the container child references to match the quantity.
    """
    settings_doc = frappe.get_doc("ICD TZ Settings")
    for item in doc.items:
        if item.item_code in [
            settings_doc.get("storage_item_single_20ft"),
            settings_doc.get("storage_item_single_40ft"),
            settings_doc.get("storage_item_double_20ft"),
            settings_doc.get("storage_item_double_40ft")
        ]:
            if item.qty < len(item.container_child_refs):
                container_child_refs = item.container_child_refs[:item.qty]
                item.container_child_refs = container_child_refs
            elif item.qty > len(item.container_child_refs):
                frappe.throw(f"Quantity of the item: <b>{item.item_code}</b> cannot be greater than the number of container child references")