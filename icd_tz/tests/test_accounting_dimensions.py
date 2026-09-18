# Copyright (c) 2026, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from icd_tz.icd_tz.api.accounting_dimensions import (
	DIMENSIONS,
	get_container_dimensions,
	get_manifest_code,
	get_posted_vouchers,
	get_submitted_purchase_orders,
)

CONTAINER_NO = "MSKU1234567"
LOOSE_CARGO_NO = "LOOSE0000001"
M_BL_NO = "MAEU123456789"
CONSIGNEE = "_Test ICD Dimension Consignee"


class TestAccountingDimensions(FrappeTestCase):
	def setUp(self):
		self.manifest = make_manifest()

	def tearDown(self):
		frappe.db.rollback()

	def test_manifest_code_drops_the_series_prefix(self):
		self.assertEqual(get_manifest_code("ICD-M-2026-00042"), "2026-00042")

	def test_manifest_code_keeps_the_amendment_suffix(self):
		self.assertEqual(get_manifest_code("ICD-M-2026-00042-1"), "2026-00042-1")

	def test_manifest_code_needs_a_numeric_part(self):
		self.assertRaises(frappe.ValidationError, get_manifest_code, "ICD-M-")

	def test_submit_creates_one_record_per_bill_of_lading(self):
		self.manifest.submit()

		master_bls = frappe.get_all("ICD Master BL", filters={"manifest": self.manifest.name}, pluck="name")
		self.assertEqual(master_bls, [f"{M_BL_NO}:{get_manifest_code(self.manifest.name)}"])

	def test_submit_creates_one_record_per_manifested_unit(self):
		self.manifest.submit()

		containers = frappe.get_all(
			"ICD Container", filters={"manifest": self.manifest.name}, pluck="container_no"
		)
		self.assertEqual(sorted(containers), sorted([CONTAINER_NO, LOOSE_CARGO_NO]))

	def test_an_lcl_box_gets_one_container_record(self):
		"""Two house bills on one box, the box is moved and costed once"""

		self.manifest.submit()

		self.assertEqual(
			frappe.db.count("ICD Container", {"manifest": self.manifest.name, "container_no": CONTAINER_NO}),
			1,
		)

	def test_loose_cargo_is_not_a_physical_container(self):
		self.manifest.submit()
		code = get_manifest_code(self.manifest.name)

		self.assertEqual(
			frappe.db.get_value("ICD Container", f"{CONTAINER_NO}:{code}", "is_physical_container"), 1
		)
		self.assertEqual(
			frappe.db.get_value("ICD Container", f"{LOOSE_CARGO_NO}:{code}", "is_physical_container"), 0
		)

	def test_container_carries_the_manifest_details(self):
		self.manifest.submit()
		container = frappe.get_doc("ICD Container", f"{CONTAINER_NO}:{get_manifest_code(self.manifest.name)}")

		self.assertEqual(container.m_bl_no, M_BL_NO)
		self.assertEqual(container.master_bl, f"{M_BL_NO}:{get_manifest_code(self.manifest.name)}")
		self.assertEqual(container.consignee, CONSIGNEE)
		self.assertEqual(container.vessel_name, self.manifest.vessel_name)
		self.assertEqual(container.size, "20")

	def test_master_bl_carries_the_consignee(self):
		self.manifest.submit()
		master_bl = frappe.get_doc("ICD Master BL", f"{M_BL_NO}:{get_manifest_code(self.manifest.name)}")

		self.assertEqual(master_bl.consignee, CONSIGNEE)
		self.assertEqual(master_bl.cargo_classification, "IM")
		self.assertEqual(master_bl.posting_date, getdate(self.manifest.arrival_date))

	def test_cancel_revokes_the_dimension_records(self):
		self.manifest.submit()
		self.manifest.cancel()

		self.assertEqual(frappe.db.count("ICD Container", {"manifest": self.manifest.name}), 0)
		self.assertEqual(frappe.db.count("ICD Master BL", {"manifest": self.manifest.name}), 0)

	def test_amendment_creates_its_own_records(self):
		self.manifest.submit()
		self.manifest.cancel()

		amended = frappe.copy_doc(self.manifest)
		amended.amended_from = self.manifest.name
		amended.docstatus = 0
		amended.insert()
		amended.submit()

		self.assertNotEqual(amended.name, self.manifest.name)
		self.assertEqual(
			frappe.db.count("ICD Container", {"manifest": amended.name}),
			2,
		)

	def test_a_manifest_without_gl_entries_has_no_posted_vouchers(self):
		self.manifest.submit()

		self.assertEqual(get_posted_vouchers(self.manifest.name), [])

	def test_a_submitted_purchase_order_blocks_cancellation(self):
		"""A Purchase Order posts no GL Entry, it is caught on its own dimension fields"""

		self.manifest.submit()
		purchase_order = make_purchase_order(
			self.manifest, f"{CONTAINER_NO}:{get_manifest_code(self.manifest.name)}"
		)
		purchase_order.submit()

		self.assertEqual(
			get_submitted_purchase_orders(self.manifest.name), [("Purchase Order", purchase_order.name)]
		)
		self.assertEqual(get_posted_vouchers(self.manifest.name), [])
		self.assertRaises(frappe.ValidationError, self.manifest.cancel)

	def test_a_draft_purchase_order_does_not_block_cancellation(self):
		self.manifest.submit()
		make_purchase_order(self.manifest, f"{CONTAINER_NO}:{get_manifest_code(self.manifest.name)}")

		self.assertEqual(get_submitted_purchase_orders(self.manifest.name), [])

	def test_one_container_under_two_bills_is_rejected(self):
		"""Costs booked on it could not be attributed to one bill, so the manifest is refused"""

		self.manifest.append(
			"containers",
			{"m_bl_no": "MAEU000000000", "container_no": CONTAINER_NO, "type_of_container": "C"},
		)
		self.manifest.save()

		self.assertRaises(frappe.ValidationError, self.manifest.submit)

	def test_a_repeated_container_row_on_one_bill_is_tolerated(self):
		self.manifest.append(
			"containers",
			{"m_bl_no": M_BL_NO, "container_no": CONTAINER_NO, "type_of_container": "C"},
		)
		self.manifest.save()
		self.manifest.submit()

		self.assertEqual(
			frappe.db.count("ICD Container", {"manifest": self.manifest.name, "container_no": CONTAINER_NO}),
			1,
		)

	def test_container_type_is_read_past_casing_and_padding(self):
		self.manifest.containers[0].type_of_container = " c "
		self.manifest.save()
		self.manifest.submit()

		self.assertEqual(
			frappe.db.get_value(
				"ICD Container",
				f"{CONTAINER_NO}:{get_manifest_code(self.manifest.name)}",
				"is_physical_container",
			),
			1,
		)

	def test_both_dimensions_are_registered(self):
		for doctype, fieldname in DIMENSIONS.items():
			dimension = frappe.db.get_value(
				"Accounting Dimension", {"document_type": doctype}, ["fieldname", "disabled"], as_dict=True
			)
			self.assertIsNotNone(dimension, doctype)
			self.assertEqual(dimension.fieldname, fieldname)
			self.assertEqual(dimension.disabled, 0, f"{doctype} dimension is disabled")

	def test_the_dimension_fields_reach_the_purchase_doctypes(self):
		for doctype in ("Purchase Order", "Purchase Order Item", "Purchase Invoice", "GL Entry"):
			for fieldname in DIMENSIONS.values():
				self.assertTrue(frappe.db.has_column(doctype, fieldname), f"{doctype} is missing {fieldname}")

	def test_users_cannot_create_dimension_records_from_the_form(self):
		for doctype in DIMENSIONS:
			self.assertEqual(frappe.get_meta(doctype).in_create, 1, doctype)

	def test_every_dimension_field_is_read_only(self):
		layout_fieldtypes = ("Section Break", "Column Break", "Tab Break")

		for doctype in DIMENSIONS:
			for field in frappe.get_meta(doctype).fields:
				if field.fieldtype in layout_fieldtypes:
					continue

				self.assertEqual(field.read_only, 1, f"{doctype}.{field.fieldname}")

	def test_charge_row_dimensions_resolve_to_the_records(self):
		self.manifest.submit()
		code = get_manifest_code(self.manifest.name)
		source = frappe._dict(
			{"manifest": self.manifest.name, "container_no": CONTAINER_NO, "m_bl_no": M_BL_NO}
		)

		self.assertEqual(
			get_container_dimensions(source),
			{"icd_container": f"{CONTAINER_NO}:{code}", "icd_master_bl": f"{M_BL_NO}:{code}"},
		)

	def test_charge_row_dimensions_stay_blank_for_an_unbackfilled_manifest(self):
		"""Manifests submitted before the dimensions existed must not break the order"""

		source = frappe._dict(
			{"manifest": "ICD-M-2019-00001", "container_no": CONTAINER_NO, "m_bl_no": M_BL_NO}
		)

		self.assertEqual(get_container_dimensions(source), {})


def make_manifest():
	manifest = frappe.new_doc("Manifest")
	manifest.update(
		{
			"manifest": "/private/files/_test_icd_manifest.xlsx",
			"company": get_company(),
			"mrn": "_TEST-MRN-001",
			"vessel_name": "_Test Vessel",
			"voyage_no": "V-001",
			"arrival_date": "2026-09-01",
			"port": "DP WORLD",
		}
	)

	manifest.append(
		"master_bl",
		{
			"m_bl_no": M_BL_NO,
			"cargo_classification": "IM",
			"place_of_destination": "TZDAR",
			"place_of_delivery": "WITZDL019",
			"port_of_loading": "CNSHA",
			"number_of_containers": "2",
			"cargo_description": "_Test cargo",
			"consignee_name": CONSIGNEE,
			"consignee_tin": "123456789",
			"shipping_agent_code": "MAEU",
			"shipping_agent_name": "_Test Shipping Agent",
		},
	)

	for container_no, type_of_container, size in (
		(CONTAINER_NO, "C", "20"),
		(LOOSE_CARGO_NO, "V", ""),
	):
		manifest.append(
			"containers",
			{
				"m_bl_no": M_BL_NO,
				"container_no": container_no,
				"type_of_container": type_of_container,
				"container_size": size,
				"freight_indicator": "FCL",
				"no_of_packages": "10",
				"package_unit": "PK",
				"weight": "12000",
				"weight_unit": "KG",
			},
		)

	# one box, two house bills: the LCL case
	for h_bl_no in ("HBL-001", "HBL-002"):
		manifest.append(
			"hbl_containers",
			{
				"m_bl_no": M_BL_NO,
				"h_bl_no": h_bl_no,
				"container_no": CONTAINER_NO,
				"type_of_container": "C",
				"container_size": "20",
			},
		)
		manifest.append(
			"house_bl",
			{"m_bl_no": M_BL_NO, "h_bl_no": h_bl_no, "consignee_name": CONSIGNEE},
		)

	manifest.insert()
	return manifest


def make_purchase_order(manifest, container_dimension):
	"""A transport cost booked against the container before it is received"""

	purchase_order = frappe.new_doc("Purchase Order")
	purchase_order.update(
		{
			"supplier": get_supplier(),
			"company": manifest.company,
			"transaction_date": manifest.arrival_date,
			"schedule_date": manifest.arrival_date,
		}
	)
	purchase_order.append(
		"items",
		{
			"item_code": get_service_item(),
			"qty": 1,
			"rate": 150000,
			"schedule_date": manifest.arrival_date,
			"icd_container": container_dimension,
		},
	)
	purchase_order.insert()
	return purchase_order


def get_supplier():
	supplier = frappe.db.get_value("Supplier", {}, "name")
	if supplier:
		return supplier

	return frappe.get_doc({"doctype": "Supplier", "supplier_name": "_Test ICD Transporter"}).insert().name


def get_service_item():
	item = frappe.db.get_value("Item", {"is_stock_item": 0}, "name")
	if not item:
		frappe.throw("No service Item on the test site")

	return item


def get_company():
	company = frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("No Company on the test site")

	return company
