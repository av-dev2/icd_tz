# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.tests.utils import create_manifest, get_test_company


def make_manifest(containers, hbl_containers=()):
	manifest = frappe.new_doc("Manifest")
	for row in containers:
		manifest.append("containers", {"type_of_container": "C", **row})
	for container_no in hbl_containers:
		manifest.append("hbl_containers", {"container_no": container_no})
	return manifest


class TestManifest(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_a_manifest_without_a_file_is_rejected(self):
		manifest = frappe.get_doc({"doctype": "Manifest", "company": get_test_company()})
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


class TestManifestDashboard(IntegrationTestCase):
	"""The reception progress card counts each container by its freight"""

	def test_an_lcl_container_without_house_bills_counts_as_lcl(self):
		manifest = make_manifest(
			[
				{"container_no": "FCLU0000001", "freight_indicator": "FCL"},
				{"container_no": "LCLU0000001", "freight_indicator": "LCL"},
			]
		)

		data = manifest.get_dashboard_data()

		self.assertEqual((data["total_fcl"], data["total_lcl"]), (1, 1))

	def test_a_container_with_house_bills_counts_as_lcl(self):
		manifest = make_manifest(
			[{"container_no": "HBLU0000001", "freight_indicator": "FCL"}], hbl_containers=["HBLU0000001"]
		)

		self.assertEqual(manifest.get_dashboard_data()["total_lcl"], 1)
