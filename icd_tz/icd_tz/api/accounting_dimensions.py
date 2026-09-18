"""Manifest-grained accounting dimensions.

ICD Container and ICD Master BL exist so a Purchase Order or Purchase Invoice can be
costed against a container or a bill of lading before the Container record is created
at Container Reception.
"""

import re

import frappe

# Accounting Dimension fieldname is scrub(document_type)
DIMENSIONS = {"ICD Container": "icd_container", "ICD Master BL": "icd_master_bl"}


def get_manifest_code(manifest: str) -> str:
	"""Manifest name without its series prefix, ICD-M-2026-00042 becomes 2026-00042"""

	code = re.sub(r"^\D+", "", manifest or "")
	if not code:
		frappe.throw(
			f"Manifest <b>{manifest}</b> has no numeric part, a dimension ID cannot be built from it"
		)

	return code


def get_container_dimensions(source) -> dict:
	"""Dimension values for a charge row, keyed by the source container_no, m_bl_no and manifest

	Manifests submitted before these dimensions existed carry no records. Their rows are
	left blank rather than pointing the order at a name that does not resolve.
	"""

	if not source.manifest or not source.container_no:
		return {}

	manifest_code = get_manifest_code(source.manifest)
	values = {}

	container = f"{source.container_no}:{manifest_code}"
	if frappe.db.exists("ICD Container", container):
		values["icd_container"] = container

	if source.m_bl_no:
		master_bl = f"{source.m_bl_no}:{manifest_code}"
		if frappe.db.exists("ICD Master BL", master_bl):
			values["icd_master_bl"] = master_bl

	return values


def create_dimension_records(manifest_doc):
	"""Create one ICD Master BL per bill of lading and one ICD Container per manifested unit"""

	consignees = get_known_consignees(manifest_doc)
	master_bl_names = create_master_bls(manifest_doc, consignees)
	create_containers(manifest_doc, master_bl_names, consignees)


def get_known_consignees(manifest_doc) -> set:
	"""Consignee names on the manifest that resolve to a Consignee record

	Consignee is named after consignee_name, so the manifest value is the link value.
	Resolved in one query, a manifest can carry hundreds of container rows.
	"""

	names = {row.consignee_name for row in manifest_doc.master_bl if row.consignee_name}
	if not names:
		return set()

	return set(frappe.get_all("Consignee", filters={"name": ["in", list(names)]}, pluck="name"))


def create_master_bls(manifest_doc, consignees: set) -> dict:
	"""Returns the ICD Master BL name of every M BL No on the manifest"""

	names = {}
	for row in manifest_doc.master_bl:
		if not row.m_bl_no or row.m_bl_no in names:
			continue

		doc = frappe.new_doc("ICD Master BL")
		doc.update(
			{
				"m_bl_no": row.m_bl_no,
				"manifest": manifest_doc.name,
				"posting_date": manifest_doc.arrival_date,
				"company": manifest_doc.company,
				"consignee": row.consignee_name if row.consignee_name in consignees else None,
				"cargo_classification": row.cargo_classification,
				"number_of_containers": row.number_of_containers,
				"place_of_destination": row.place_of_destination,
				"place_of_delivery": row.place_of_delivery,
				"port_of_loading": row.port_of_loading,
				"cargo_description": row.cargo_description,
				"vessel_name": manifest_doc.vessel_name,
				"voyage_no": manifest_doc.voyage_no,
				"shipping_agent_code": row.shipping_agent_code,
				"shipping_agent_name": row.shipping_agent_name,
			}
		)
		doc.insert(ignore_permissions=True)
		names[row.m_bl_no] = doc.name

	return names


def create_containers(manifest_doc, master_bl_names: dict, consignees: set):
	"""One record per manifested unit, loose cargo and vehicles included

	The HBL Container rows are deliberately left out. An LCL box carries many house bills
	but it is moved and costed once, so it gets one dimension value.
	"""

	bl_consignees = {row.m_bl_no: row.consignee_name for row in manifest_doc.master_bl}

	seen = {}
	for row in manifest_doc.containers:
		if not row.container_no:
			continue

		if row.container_no in seen:
			validate_one_bill_of_lading(row, seen[row.container_no])
			continue

		consignee_name = bl_consignees.get(row.m_bl_no)
		doc = frappe.new_doc("ICD Container")
		doc.update(
			{
				"container_no": row.container_no,
				"manifest": manifest_doc.name,
				"posting_date": manifest_doc.arrival_date,
				"company": manifest_doc.company,
				"m_bl_no": row.m_bl_no,
				"master_bl": master_bl_names.get(row.m_bl_no),
				"consignee": consignee_name if consignee_name in consignees else None,
				"type_of_container": row.type_of_container,
				"size": row.container_size,
				"freight_indicator": row.freight_indicator,
				"is_physical_container": 1 if is_container_type(row.type_of_container) else 0,
				"no_of_packages": row.no_of_packages,
				"package_unit": row.package_unit,
				"weight": row.weight,
				"weight_unit": row.weight_unit,
				"vessel_name": manifest_doc.vessel_name,
				"voyage_no": manifest_doc.voyage_no,
				"arrival_date": manifest_doc.arrival_date,
			}
		)
		doc.insert(ignore_permissions=True)
		seen[row.container_no] = row.m_bl_no


def validate_one_bill_of_lading(row, first_m_bl_no: str | None):
	"""A repeated container row is only safe while it names the same bill of lading

	The dimension is one record per container per manifest. If the manifest puts one
	container under two bills, every cost booked on it would land on whichever bill was
	read first, so the manifest is rejected instead.
	"""

	if row.m_bl_no == first_m_bl_no:
		return

	frappe.throw(
		f"Container <b>{row.container_no}</b> appears on this manifest under two bills of lading: "
		f"<b>{first_m_bl_no}</b> and <b>{row.m_bl_no}</b>."
		"<br>Correct the manifest file, its costs cannot be attributed to one bill."
	)


def is_container_type(type_of_container: str | None) -> bool:
	"""Manifest files arrive with inconsistent casing and padding, C marks a real container"""

	return (type_of_container or "").strip().upper() == "C"


def validate_manifest_not_in_accounts(manifest: str):
	"""Block cancellation once the manifest is carried by accounting documents"""

	blockers = get_posted_vouchers(manifest) + get_submitted_purchase_orders(manifest)
	if not blockers:
		return

	document_list = ", ".join(f"<b>{doctype}: {name}</b>" for doctype, name in blockers)
	frappe.throw(
		f"Manifest <b>{manifest}</b> is already used in accounting documents: {document_list}. "
		"<br>Cancel those documents first, this manifest cannot be cancelled."
	)


def get_posted_vouchers(manifest: str) -> list:
	"""Vouchers whose GL Entries carry this manifest, through the manifest field or a dimension"""

	filter_sets = get_dimension_filters("GL Entry", get_dimension_names(manifest))
	if frappe.db.has_column("GL Entry", "manifest"):
		filter_sets.append({"manifest": manifest})

	vouchers = set()
	for filters in filter_sets:
		vouchers.update(
			(row.voucher_type, row.voucher_no)
			for row in frappe.get_all(
				"GL Entry",
				filters={**filters, "is_cancelled": 0},
				fields=["voucher_type", "voucher_no"],
				distinct=True,
			)
		)

	return sorted(vouchers)


def get_submitted_purchase_orders(manifest: str) -> list:
	"""Purchase Orders carrying this manifest

	A Purchase Order posts no GL Entry, so it is checked on its own dimension fields
	instead, at both parent and item level.
	"""

	dimension_names = get_dimension_names(manifest)

	names = set()
	for doctype, name_field in (("Purchase Order", "name"), ("Purchase Order Item", "parent")):
		for filters in get_dimension_filters(doctype, dimension_names):
			names.update(frappe.get_all(doctype, filters={**filters, "docstatus": 1}, pluck=name_field))

	return sorted(("Purchase Order", name) for name in names)


def get_dimension_names(manifest: str) -> dict:
	"""The manifest dimension record names, keyed by accounting dimension fieldname"""

	return {
		fieldname: frappe.get_all(doctype, filters={"manifest": manifest}, pluck="name")
		for doctype, fieldname in DIMENSIONS.items()
	}


def get_dimension_filters(doctype: str, dimension_names: dict) -> list:
	"""One filter set per ICD dimension field that doctype actually carries

	The fields only exist once create_icd_accounting_dimensions has run.
	"""

	return [
		{fieldname: ["in", names]}
		for fieldname, names in dimension_names.items()
		if names and frappe.db.has_column(doctype, fieldname)
	]


def revoke_dimension_records(manifest: str):
	"""Drop the dimension records of a cancelled manifest, the amendment creates its own set

	ICD Container is deleted first, it links to ICD Master BL.
	"""

	for doctype in DIMENSIONS:
		for name in frappe.get_all(doctype, filters={"manifest": manifest}, pluck="name"):
			frappe.delete_doc(doctype, name, ignore_permissions=True, delete_permanently=True)


def revoke_consignees(manifest_doc):
	"""Drop the consignees this manifest created, keeping any that other records still use"""

	names = {row.consignee_name for row in manifest_doc.master_bl if row.consignee_name}
	names |= {row.consignee_name for row in manifest_doc.house_bl if row.consignee_name}

	kept = []
	for name in sorted(names):
		if not frappe.db.exists("Consignee", name):
			continue

		try:
			frappe.delete_doc("Consignee", name, ignore_permissions=True)
		except frappe.LinkExistsError:
			kept.append(name)

	if kept:
		frappe.msgprint(
			f"Consignee: <b>{', '.join(kept)}</b> is still used by other records and was kept.",
			indicator="orange",
		)
