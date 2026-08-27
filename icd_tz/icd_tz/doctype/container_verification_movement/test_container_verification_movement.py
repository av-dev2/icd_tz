# Copyright (c) 2024, elius mgani and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from icd_tz.tests.utils import create_container, create_icd_tz_settings


class TestContainerVerificationMovement(IntegrationTestCase):
	def setUp(self):
		create_icd_tz_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_a_movement_records_its_container(self):
		container = create_container()
		movement = frappe.get_doc(
			{
				"doctype": "Container Verification Movement",
				"container_id": container.name,
				"container_no": container.container_no,
			}
		).insert(ignore_permissions=True)

		self.assertEqual(movement.container_id, container.name)

	def test_a_movement_is_submittable(self):
		self.assertEqual(frappe.get_meta("Container Verification Movement").is_submittable, 1)
