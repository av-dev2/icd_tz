# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestDocumentType(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_a_document_type_is_named_after_itself(self):
		document_type = frappe.get_doc(
			{"doctype": "Document Type", "document_type_name": "ICD Test Bill of Lading"}
		).insert(ignore_permissions=True)

		self.assertEqual(document_type.name, "ICD Test Bill of Lading")
