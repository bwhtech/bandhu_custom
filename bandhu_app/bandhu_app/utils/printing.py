import frappe
from frappe.core.doctype.access_log.access_log import make_access_log


def render_print(doctype: str, name: str, print_format: str, access_method: str) -> str:
	make_access_log(doctype=doctype, document=name, method=access_method)

	frappe.flags.ignore_print_permissions = True
	try:
		return frappe.get_print(doctype, name, print_format=print_format, no_letterhead=True)
	finally:
		frappe.flags.ignore_print_permissions = False
