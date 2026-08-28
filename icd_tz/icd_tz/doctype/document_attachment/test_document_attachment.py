# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestDocumentAttachment(IntegrationTestCase):
	def test_document_attachment_is_a_child_table(self):
		self.assertEqual(frappe.get_meta("Document Attachment").istable, 1)

	def test_document_attachment_links_a_document_type(self):
		self.assertEqual(
			frappe.get_meta("Document Attachment").get_field("document_type").options, "Document Type"
		)
