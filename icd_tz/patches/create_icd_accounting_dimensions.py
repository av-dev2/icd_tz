import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	make_dimension_in_accounting_doctypes,
)

from icd_tz.icd_tz.api.accounting_dimensions import DIMENSIONS


def execute():
	"""Add ICD Container and ICD Master BL as accounting dimensions

	They let a Purchase Order or Purchase Invoice be costed per container or per bill of
	lading while the Container record does not exist yet.
	"""

	for document_type in DIMENSIONS:
		if frappe.db.exists("Accounting Dimension", {"document_type": document_type}):
			continue

		dimension = frappe.new_doc("Accounting Dimension")
		dimension.document_type = document_type
		dimension.flags.ignore_permissions = True
		dimension.insert()

		# on_update only queues the field creation, run it here so the fields exist once the patch ends
		make_dimension_in_accounting_doctypes(doc=dimension)

		print(f"Added the {document_type} accounting dimension, field: {dimension.fieldname}")
