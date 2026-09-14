// Copyright (c) 2026, elius mgani and contributors
// For license information, please see license.txt

frappe.ui.form.on("EDI Partner", {
  test_connection(frm) {
    if (frm.is_dirty()) {
      frappe.msgprint(
        __("Please save the record before testing the connection")
      );
      return;
    }

    frappe.call({
      method: "try_edi_connection",
      doc: frm.doc,
      freeze: true,
      freeze_message: __("Testing EDI connection..."),
      callback: (r) => {
        if (r.message && r.message.success) {
          frappe.msgprint({
            title: __("Success"),
            message: r.message.message,
            indicator: "green",
          });
        }
      },
    });
  },
});
