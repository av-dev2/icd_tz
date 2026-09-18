# Copyright (c) 2026, elius mgani and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from icd_tz.icd_tz.api.accounting_dimensions import get_manifest_code


class ICDMasterBL(Document):
	"""Accounting dimension value for one master bill of lading, MAEU123456789:2026-00042"""

	def autoname(self):
		self.name = f"{self.m_bl_no}:{get_manifest_code(self.manifest)}"
