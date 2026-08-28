# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.tests.utils import create_manifest, get_default_company


class TestManifest(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_a_manifest_without_a_file_is_rejected(self):
		manifest = frappe.get_doc({"doctype": "Manifest", "company": get_default_company()})
		self.assertRaises(frappe.ValidationError, manifest.insert)

	def test_the_manifest_file_cannot_be_removed_later(self):
		manifest = create_manifest()
		manifest.manifest = ""

		self.assertRaises(frappe.ValidationError, manifest.save)

	def test_submitting_without_a_port_is_rejected(self):
		manifest = create_manifest()
		manifest.db_set("port", "")
		manifest.reload()

		self.assertRaises(frappe.ValidationError, manifest.submit)

	def test_submitting_creates_a_consignee_for_every_master_bill(self):
		manifest = create_manifest()
		manifest.master_bl[0].consignee_name = "ICD Test Manifest Consignee"
		manifest.save()
		manifest.submit()

		self.assertTrue(frappe.db.exists("Consignee", "ICD Test Manifest Consignee"))
