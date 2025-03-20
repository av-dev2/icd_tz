# Copyright (c) 2024, elius mgani and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_fullname, nowdate, nowtime
from icd_tz.icd_tz.api.utils import validate_cf_agent, validate_draft_doc


class GatePass(Document):
	def validate(self):
		validate_cf_agent(self)
	
	def before_submit(self):

		# self.validate_container_charges()
		# self.validate_in_yard_booking()
		# self.validate_reception_charges()

		self.validate_container_charges()
		self.validate_in_yard_booking()
		self.validate_reception_charges()
		self.validate_mandatory_fields()
		self.update_submitted_info()
	
	def on_submit(self):
		self.update_container_status()

	def validate_container_charges(self):
		"""Validate the storage payments for the Gate Pass"""

		container_info = frappe.db.get_value(
			"Container",
			self.container_id,
			["has_removal_charges", "r_sales_invoice", "has_corridor_levy_charges", "c_sales_invoice", "days_to_be_billed"],
			as_dict=True
		)

		if container_info.days_to_be_billed > 0:
			frappe.throw(
				f"There are <b>{container_info.days_to_be_billed}</b> days to be billed for this container.<br>\
				Please clear storage payment dues before issuing the Gate Pass."
			)
		
		if container_info.has_removal_charges == "Yes" and not container_info.r_sales_invoice:
			frappe.throw(
				"Payment for Removal charge were not done. Please clear the payment before issuing the Gate Pass."
			)
		
		if container_info.has_corridor_levy_charges == "Yes" and not container_info.c_sales_invoice:
			frappe.throw(
				"Payment for Corridor Levy charge were not done. Please clear the payment before issuing the Gate Pass."
			)
	
	def validate_in_yard_booking(self):
		"""Validate the In Yard Container Booking for the Gate Pass"""

		booking_info = frappe.db.get_value(
			"In Yard Container Booking",
			{"container_id": self.container_id},
			["has_stripping_charges", "s_sales_invoice", "has_custom_verification_charges", "cv_sales_invoice"],
			as_dict=True
		)
		if booking_info.has_stripping_charges == "Yes" and not booking_info.s_sales_invoice:
			frappe.throw(
				"Payment for Stripping charge were not done. Please clear the payment before issuing the Gate Pass."
			)
		
		if booking_info.has_custom_verification_charges == "Yes" and not booking_info.cv_sales_invoice:
			frappe.throw(
				"Payment for Custom Verification charge were not done. Please clear the payment before issuing the Gate Pass."
			)
	
	def validate_reception_charges(self):
		"""Validate the Reception Charges for the Gate Pass"""

		container_reception = frappe.db.get_value(
			"Container",
			self.container_id,
			"container_reception"
		)
		if not container_reception:
			return
		
		reception_info = frappe.db.get_value(
			"Container Reception",
			container_reception,
			["has_transport_charges", "t_sales_invoice", "has_shore_handling_charges", "s_sales_invoice"],
			as_dict=True
		)

		if reception_info.has_transport_charges == "Yes" and not reception_info.t_sales_invoice:
			frappe.throw(
				"Payment for Transport charge were not done. Please clear the payment before issuing the Gate Pass."
			)
		
		if reception_info.has_shore_handling_charges == "Yes" and not reception_info.s_sales_invoice:
			frappe.throw(
				"Payment for Shore Handling charge were not done. Please clear the payment before issuing the Gate Pass."
			)

	def update_container_status(self):
		if not self.container_id:
			return
		
		frappe.db.set_value(
			"Container",
			self.container_id,
			"status",
			"Delivered"
		)

	def update_submitted_info(self):
		self.submitted_by = get_fullname(frappe.session.user)
		self.submitted_date = nowdate()
		self.submitted_time = nowtime()
	
	def validate_mandatory_fields(self):
		fields_str = ""
		fields = ["transporter", "truck", "trailer", "driver_name", "license_no"]
		for field in fields:
			if not self.get(field):
				fields_str += f"{self.meta.get_label(field)}, "
		
		if fields_str:
			frappe.throw(f"Please ensure the following fields are filled before submitting this document: <b>{fields_str}</b>")
