# Copyright (c) 2026, elius mgani and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from icd_tz.icd_tz.api.accounting_dimensions import get_manifest_code


class ICDContainer(Document):
	"""Accounting dimension value for one manifested unit, MSKU1234567:2026-00042"""

	def autoname(self):
		self.name = f"{self.container_no}:{get_manifest_code(self.manifest)}"
