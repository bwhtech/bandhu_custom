import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, Date
from frappe.utils import today

HELPLINE_ROLES = {"Helpline Staff", "System Manager"}
OPEN_STATUSES = ("Pending", "In Progress")
FOLLOW_UP_STATUSES = ("In Progress", "Completed", "Lost")
REQUIRED_ACTION_FROM = ("None", "Programme", "Clinic")
FOLLOW_UP_LIST_LIMIT = 200


def require_helpline_access() -> None:
	if not HELPLINE_ROLES.intersection(frappe.get_roles()):
		frappe.throw(_("You do not have permission to access this page."), frappe.PermissionError)


@frappe.whitelist()
def get_follow_up_list() -> dict:
	require_helpline_access()
	frappe.has_permission("Referral", "read", throw=True)

	referral = frappe.qb.DocType("Referral")
	follow_up = frappe.qb.DocType("Referral Followup")
	latest_next_date = (
		frappe.qb.from_(follow_up)
		.select(follow_up.next_followup_date)
		.where((follow_up.parent == referral.name) & (follow_up.parenttype == "Referral"))
		.orderby(follow_up.idx, order=frappe.qb.desc)
		.limit(1)
	)
	due_date = Coalesce(latest_next_date, Date(referral.created_on))
	referrals = (
		frappe.qb.from_(referral)
		.select(
			referral.name,
			referral.patient,
			referral.referred_to,
			referral.reason,
			referral.priority,
			referral.status,
			referral.required_action_from,
			due_date.as_("due_date"),
		)
		.where((referral.helpline_flag == 1) & referral.status.isin(OPEN_STATUSES))
		.orderby(due_date)
		.limit(FOLLOW_UP_LIST_LIMIT + 1)
		.run(as_dict=True)
	)
	capped = len(referrals) > FOLLOW_UP_LIST_LIMIT
	referrals = referrals[:FOLLOW_UP_LIST_LIMIT]
	if not referrals:
		return {"referrals": [], "capped": False}

	calls_by_referral = {}
	for call in frappe.get_all(
		"Referral Followup",
		filters={"parenttype": "Referral", "parent": ["in", [row.name for row in referrals]]},
		fields=["parent", "followup_date", "summary", "next_followup_date"],
		order_by="idx asc",
	):
		calls_by_referral.setdefault(call.parent, []).append(call)

	patients = {
		row.name: row
		for row in frappe.get_all(
			"Patient",
			filters={"name": ["in", list({row.patient for row in referrals})]},
			fields=["name", "patient_name", "custom_bandhu_id", "mobile"],
		)
	}

	for referral_row in referrals:
		patient = patients.get(referral_row.patient) or frappe._dict()
		referral_row.patient_name = patient.patient_name or referral_row.patient
		referral_row.clinic_id = patient.custom_bandhu_id
		referral_row.mobile = patient.mobile
		referral_row.calls = calls_by_referral.get(referral_row.name, [])

	return {"referrals": referrals, "capped": capped}


@frappe.whitelist(methods=["POST"])
def log_follow_up(
	referral: str,
	summary: str,
	status: str = "In Progress",
	next_followup_date: str | None = None,
	required_action_from: str | None = None,
) -> None:
	require_helpline_access()

	if status not in FOLLOW_UP_STATUSES:
		frappe.throw(_("Choose a valid status."))
	if required_action_from and required_action_from not in REQUIRED_ACTION_FROM:
		frappe.throw(_("Choose who the action is required from."))

	referral_doc = frappe.get_doc("Referral", referral)
	referral_doc.check_permission("write")
	referral_doc.append(
		"referral_followup",
		{
			"followup_date": today(),
			"summary": summary,
			"next_followup_date": next_followup_date if status == "In Progress" else None,
		},
	)
	referral_doc.status = status
	if required_action_from:
		referral_doc.required_action_from = required_action_from
	referral_doc.save()
