"""Shared bootstrap and record factories for the icd_tz test suite."""

import frappe
from erpnext import get_default_company
from frappe.utils import nowdate, nowtime


def get_test_company() -> str:
	"""The company every ICD test record and its ICD Setting belong to"""

	company = get_default_company()
	if not company:
		frappe.throw("Set a Default Company in Global Defaults on the test site")

	return company


def get_test_icd_setting(company: str | None = None):
	"""The ICD Setting of the test company, created on first use"""

	company = company or get_test_company()
	name = frappe.db.get_value("ICD Setting", {"company": company})
	if name:
		return frappe.get_doc("ICD Setting", name)

	settings_doc = frappe.new_doc("ICD Setting")
	settings_doc.update({"company": company, "icd_code": "_TEST", "gate_pass_expiry_hours": 48})
	settings_doc.flags.ignore_mandatory = True
	settings_doc.insert(ignore_permissions=True)

	return settings_doc


def set_test_icd_setting(values: dict, company: str | None = None):
	"""Write values to the ICD Setting of the test company, so the next read sees them"""

	name = get_test_icd_setting(company).name
	frappe.db.set_value("ICD Setting", name, values)
	frappe.clear_document_cache("ICD Setting", name)


def set_item_accounts(
	item_code: str, wip_account: str | None, cogs_account: str | None, company: str | None = None
):
	"""Set the WIP and COGS Accounts of the item for the company, without the save checks"""

	company = company or get_test_company()
	row = frappe.db.get_value("Item Default", {"parenttype": "Item", "parent": item_code, "company": company})
	if row:
		frappe.db.set_value("Item Default", row, {"wip_account": wip_account, "cogs_account": cogs_account})
	else:
		item = frappe.get_doc("Item", item_code)
		item.append(
			"item_defaults", {"company": company, "wip_account": wip_account, "cogs_account": cogs_account}
		)
		item.db_update_all()

	frappe.clear_document_cache("Item", item_code)


def make_test_account(account_name: str, root_type: str, company: str | None = None) -> str:
	"""A ledger account of the test company under a group of the root type, created on first use"""

	company = company or get_test_company()
	abbr = frappe.get_cached_value("Company", company, "abbr")
	name = f"{account_name} - {abbr}"
	if frappe.db.exists("Account", name):
		return name

	parent = frappe.db.get_value(
		"Account", {"company": company, "is_group": 1, "root_type": root_type}, "name", order_by="lft desc"
	)
	frappe.get_doc(
		{"doctype": "Account", "account_name": account_name, "parent_account": parent, "company": company}
	).insert(ignore_permissions=True)

	return name


def make_test_item(item_code: str) -> str:
	"""A non-stock Item, created on first use"""

	if not frappe.db.exists("Item", item_code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"is_stock_item": 0,
			}
		).insert(ignore_permissions=True)

	return item_code


def get_company_without_setting() -> str | None:
	return frappe.db.get_value(
		"Company", {"name": ("not in", frappe.get_all("ICD Setting", pluck="company"))}, "name"
	)


def get_foreign_expense_account(company: str) -> str | None:
	"""An expense ledger of another company, for the checks that refuse one"""

	other_company = frappe.db.get_value("Company", {"name": ("!=", company)}, "name")
	return frappe.db.get_value(
		"Account", {"company": other_company, "is_group": 0, "root_type": "Expense"}, "name"
	)


def insert_purchase_order(name: str, docstatus: int = 1, flagged: int = 0, company: str | None = None) -> str:
	"""A bare Purchase Order row, enough for the container expense flag"""

	frappe.db.sql(
		"""insert into `tabPurchase Order` (name, company, docstatus, supplier, is_icd_container_expense)
		values (%s, %s, %s, '_Test Supplier', %s)""",
		(name, company or get_test_company(), docstatus, flagged),
	)

	return name


def before_tests():
	"""Complete the setup wizard and the ICD Setting the controllers read on every save."""

	frappe.clear_cache()

	if not frappe.db.a_row_exists("Company"):
		from erpnext.setup.utils import before_tests as erpnext_before_tests

		erpnext_before_tests()

	create_icd_tz_settings()
	frappe.db.commit()


SERVICE_TYPES = (
	"Storage-Single",
	"Storage-Double",
	"Verification",
	"Stripping",
	"Removal",
	"Transport",
	"Shore",
	"Levy",
)


def create_icd_tz_settings():
	"""Fill the ICD Setting of the test company, which Container, Gate Pass and Sales Order code reads."""

	settings = get_test_icd_setting()
	settings.icd_code = settings.icd_code or "TZICD"
	settings.default_price_list = settings.default_price_list or "Standard Selling"
	settings.gate_pass_expiry_hours = settings.gate_pass_expiry_hours or 24
	settings.received_date_threshold_hours = settings.received_date_threshold_hours or 12

	if not settings.storage_days:
		for destination in ("Local", "Transit"):
			settings.append(
				"storage_days", {"destination": destination, "from": 1, "to": 7, "charge": "Free"}
			)
			settings.append(
				"storage_days", {"destination": destination, "from": 8, "to": 14, "charge": "Single"}
			)
			settings.append(
				"storage_days", {"destination": destination, "from": 15, "to": 30, "charge": "Double"}
			)

	if not settings.service_types:
		for size in ("20ft", "40ft"):
			for cargo_type in ("Local", "Transit"):
				for port in ("DP WORLD", "TEAGTL"):
					for service_type in SERVICE_TYPES:
						settings.append(
							"service_types",
							{
								"service_type": service_type,
								"service_name": create_service_item(f"ICD Test {service_type} {size}"),
								"size": size,
								"cargo_type": cargo_type,
								"port": port,
							},
						)

	if not settings.loose_types:
		for service_type in SERVICE_TYPES:
			settings.append(
				"loose_types",
				{
					"service_type": service_type,
					"service_name": create_service_item(f"ICD Test {service_type} LCL"),
					"cargo_type": "Local",
				},
			)

	settings.flags.ignore_mandatory = True
	settings.save(ignore_permissions=True)
	return settings


def create_service_item(item_code):
	if frappe.db.exists("Item", item_code):
		return item_code

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_code,
			"item_group": "All Item Groups",
			"stock_uom": "Nos",
			"is_stock_item": 0,
		}
	)
	item.insert(ignore_permissions=True)
	return item.name


def create_container_location(location_name="ICD Test Yard"):
	if frappe.db.exists("Container Location", location_name):
		return location_name

	return (
		frappe.get_doc({"doctype": "Container Location", "location_name": location_name})
		.insert(ignore_permissions=True)
		.name
	)


def create_cf_company(company_name="ICD Test C&F Company"):
	if frappe.db.exists("Clearing and Forwarding Company", company_name):
		return company_name

	return (
		frappe.get_doc(
			{
				"doctype": "Clearing and Forwarding Company",
				"company_name": company_name,
				"phone": "255700000000",
				"email": "cf@example.com",
				"physical_address": "Dar es Salaam",
				"person_name": "Test Person",
				"license_no": "LIC-0001",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def create_clearing_agent(agent_name="ICD Test Agent", c_and_f_company=None):
	if frappe.db.exists("Clearing Agent", agent_name):
		return agent_name

	return (
		frappe.get_doc(
			{
				"doctype": "Clearing Agent",
				"agent_name": agent_name,
				"c_and_f_company": c_and_f_company or create_cf_company(),
				"tafer_id": "TAFER-0001",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def create_consignee(consignee_name="ICD Test Consignee"):
	if frappe.db.exists("Consignee", consignee_name):
		return consignee_name

	return (
		frappe.get_doc({"doctype": "Consignee", "consignee_name": consignee_name})
		.insert(ignore_permissions=True)
		.name
	)


def create_manifest(container_no="TESU1234567", m_bl_no="MBL-TEST-001", submit=False):
	"""Manifest refuses to save without an attached file, the value itself is never read back on save."""

	manifest = frappe.get_doc(
		{
			"doctype": "Manifest",
			"manifest": "/private/files/icd-test-manifest.xlsx",
			"company": get_test_company(),
			"vessel_name": "MV Test",
			"voyage_no": "V001",
			"port": "DP WORLD",
			"arrival_date": nowdate(),
		}
	)
	manifest.append(
		"containers",
		{
			"container_no": container_no,
			"m_bl_no": m_bl_no,
			"type_of_container": "22G1",
			"freight_indicator": "FCL",
		},
	)
	manifest.append(
		"master_bl",
		{"m_bl_no": m_bl_no, "place_of_destination": "TZDAR", "cargo_classification": "IM"},
	)
	manifest.insert(ignore_permissions=True)

	if submit:
		manifest.submit()

	return manifest


def create_movement_order(manifest=None, container_no="TESU1234567", m_bl_no="MBL-TEST-001", submit=True):
	manifest_doc = manifest or create_manifest(container_no=container_no, m_bl_no=m_bl_no)

	order = frappe.get_doc(
		{
			"doctype": "Container Movement Order",
			"company": get_test_company(),
			"manifest": manifest_doc.name,
			"movement_date": nowdate(),
			"transporter": create_supplier(),
			"driver": create_driver(),
			"truck": create_vehicle("ICD-TRUCK-01"),
			"trailer": create_vehicle("ICD-TRAILER-01"),
			"container_no": container_no,
			"m_bl_no": m_bl_no,
			"icd_time_in": nowtime(),
			"port_time_out": nowtime(),
			"ship_dc_date": nowdate(),
			"freight_indicator": "FCL",
			"cargo_type": "Local",
			"container_count": "1/1",
			"size": "20ft",
		}
	)
	order.insert(ignore_permissions=True)

	if submit:
		order.submit()

	return order


def create_container_reception(movement_order=None, submit=False, **kwargs):
	order = movement_order or create_movement_order()

	values = {
		"doctype": "Container Reception",
		"company": get_test_company(),
		"manifest": order.manifest,
		"movement_order": order.name,
		"container_no": order.container_no,
		"m_bl_no": order.m_bl_no,
		"container_location": create_container_location(),
		"country_of_destination": "Tanzania",
		"place_of_destination": "Local",
		"posting_date": nowdate(),
		"ship_dc_date": nowdate(),
		"size": "20ft",
		"weight": "2000",
		"freight_indicator": "FCL",
		"cargo_type": "Local",
		"clerk": create_employee(),
	}
	values.update(kwargs)

	reception = frappe.get_doc(values)
	reception.insert(ignore_permissions=True)

	if submit:
		reception.submit()

	return reception


def create_container(container_reception=None, **kwargs):
	"""A Container always belongs to a Container Reception, its before_save reads that link."""

	reception = container_reception or create_container_reception()

	values = {
		"doctype": "Container",
		"container_reception": reception.name,
		"container_no": reception.container_no,
		"manifest": reception.manifest,
		"m_bl_no": reception.m_bl_no,
		"company": reception.company,
		"size": reception.size,
		"status": "In Yard",
		"place_of_destination": reception.place_of_destination,
		"country_of_destination": reception.country_of_destination,
		"received_date": reception.received_date or nowdate(),
		"original_location": reception.container_location,
		"current_location": reception.container_location,
	}
	values.update(kwargs)

	container = frappe.get_doc(values)
	container.append("container_dates", {"date": values["received_date"]})
	container.insert(ignore_permissions=True)
	return container


def create_supplier(supplier_name="ICD Test Transporter"):
	if frappe.db.exists("Supplier", supplier_name):
		return supplier_name

	return (
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": supplier_name,
				"supplier_group": "All Supplier Groups",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def create_driver(full_name="ICD Test Driver"):
	existing = frappe.db.get_value("Driver", {"full_name": full_name}, "name")
	if existing:
		return existing

	return (
		frappe.get_doc({"doctype": "Driver", "full_name": full_name, "license_number": "DL-0001"})
		.insert(ignore_permissions=True)
		.name
	)


def create_vehicle(license_plate):
	if frappe.db.exists("Vehicle", license_plate):
		return license_plate

	return (
		frappe.get_doc(
			{
				"doctype": "Vehicle",
				"license_plate": license_plate,
				"make": "Test",
				"model": "Test",
				"last_odometer": 0,
				"acquisition_date": nowdate(),
				"location": "Dar es Salaam",
				"chassis_no": license_plate,
				"uom": "Litre",
				"vehicle_value": 1000,
				"fuel_type": "Diesel",
				"vehicle_owner": create_supplier(),
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def create_booking(container=None, submit=False, **kwargs):
	container_doc = container or create_container()
	c_and_f_company = create_cf_company()

	values = {
		"doctype": "In Yard Container Booking",
		"container_id": container_doc.name,
		"container_no": container_doc.container_no,
		"c_and_f_company": c_and_f_company,
		"clearing_agent": create_clearing_agent(c_and_f_company=c_and_f_company),
		"consignee": create_consignee(),
		"m_bl_no": container_doc.m_bl_no,
		"inspection_date": nowdate(),
		"inspection_location": create_container_location(),
	}
	values.update(kwargs)

	booking = frappe.get_doc(values)
	booking.insert(ignore_permissions=True)

	if submit:
		booking.submit()

	return booking


def create_inspection(booking=None, submit=False, **kwargs):
	booking_doc = booking or create_booking(submit=True)

	values = {
		"doctype": "Container Inspection",
		"in_yard_container_booking": booking_doc.name,
		"container_id": booking_doc.container_id,
		"container_no": booking_doc.container_no,
		"c_and_f_company": booking_doc.c_and_f_company,
		"clearing_agent": booking_doc.clearing_agent,
		"inspection_date": nowdate(),
		"inspector_name": "ICD Test Inspector",
	}
	values.update(kwargs)

	inspection = frappe.get_doc(values)
	inspection.insert(ignore_permissions=True)

	if submit:
		inspection.submit()

	return inspection


def create_gate_pass(container=None, **kwargs):
	container_doc = container or create_container()
	c_and_f_company = create_cf_company()

	values = {
		"doctype": "Gate Pass",
		"container_id": container_doc.name,
		"container_no": container_doc.container_no,
		"manifest": container_doc.manifest,
		"m_bl_no": container_doc.m_bl_no,
		"company": container_doc.company,
		"c_and_f_company": c_and_f_company,
		"clearing_agent": create_clearing_agent(c_and_f_company=c_and_f_company),
		"consignee": create_consignee(),
	}
	values.update(kwargs)

	gate_pass = frappe.get_doc(values)
	gate_pass.insert(ignore_permissions=True)
	return gate_pass


def create_employee(employee_name="ICD Test Clerk"):
	existing = frappe.db.get_value("Employee", {"employee_name": employee_name}, "name")
	if existing:
		return existing

	first_name, last_name = employee_name.rsplit(" ", 1)

	return (
		frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first_name,
				"last_name": last_name,
				"company": get_test_company(),
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"gender": "Male",
				"status": "Active",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)
