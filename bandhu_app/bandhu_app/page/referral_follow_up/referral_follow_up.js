/* global bandhu */

const SESSION_UI_ASSET = "/assets/bandhu_app/js/session_ui.js";

const PRIORITY_THEMES = { High: "red", Medium: "orange", Low: "gray" };

let helpline_page = null;

function format_due(due_date) {
	const days = moment(due_date).startOf("day").diff(moment().startOf("day"), "days");
	if (days < 0) return bandhu.session_ui.format_badge(__("Overdue"), "red", "subtle");
	if (days === 0) return bandhu.session_ui.format_badge(__("Due today"), "orange", "subtle");
	return frappe.utils.escape_html(frappe.datetime.str_to_user(due_date));
}

function format_phone(mobile) {
	if (!mobile) return '<span class="text-muted">' + __("No number") + "</span>";
	const number = frappe.utils.escape_html(mobile);
	return '<a href="tel:' + number + '">' + number + "</a>";
}

function format_referral_row(referral, index) {
	return (
		"<tr>" +
		"<td>" +
		format_due(referral.due_date) +
		"</td>" +
		'<td><div class="patient-name">' +
		frappe.utils.escape_html(referral.patient_name || "") +
		'</div><div class="patient-meta">' +
		frappe.utils.escape_html(referral.clinic_id || "") +
		"</div></td>" +
		"<td>" +
		format_phone(referral.mobile) +
		"</td>" +
		"<td>" +
		frappe.utils.escape_html(referral.referred_to || "") +
		'<div class="patient-meta">' +
		frappe.utils.escape_html(referral.reason || "") +
		"</div></td>" +
		"<td>" +
		bandhu.session_ui.format_badge(
			__(referral.priority || "Medium"),
			PRIORITY_THEMES[referral.priority] || "gray",
			"subtle"
		) +
		"</td>" +
		'<td class="call-count">' +
		(referral.calls.length === 1 ? __("1 call") : __("{0} calls", [referral.calls.length])) +
		"</td>" +
		'<td class="row-actions"><button class="btn btn-default btn-sm follow-up-btn" data-index="' +
		index +
		'">' +
		__("Follow Up") +
		"</button></td>" +
		"</tr>"
	);
}

function format_follow_up_list(data) {
	if (!data.referrals.length) {
		return (
			'<div class="empty-state">' +
			frappe.utils.icon("circle-check", "xl", "", "", "current-color empty-state-icon") +
			'<span class="empty-state-text">' +
			__("No referrals to follow up.") +
			"</span></div>"
		);
	}

	return (
		'<h4 class="queue-head">' +
		__("Referrals to Follow Up") +
		'<span class="queue-meta">(' +
		data.referrals.length +
		")</span></h4>" +
		(data.capped
			? '<p class="text-muted">' +
			  __("Showing the first {0} cases, due first.", [data.referrals.length]) +
			  "</p>"
			: "") +
		'<div class="table-wrap"><table class="table"><thead><tr>' +
		"<th>" +
		__("Due") +
		"</th><th>" +
		__("Patient") +
		"</th><th>" +
		__("Mobile Number") +
		"</th><th>" +
		__("Referred To") +
		"</th><th>" +
		__("Priority") +
		"</th><th>" +
		__("Call History") +
		"</th><th></th></tr></thead><tbody>" +
		data.referrals.map(format_referral_row).join("") +
		"</tbody></table></div>"
	);
}

function format_call_history(referral) {
	if (!referral.calls.length) {
		return '<p class="text-muted">' + __("No calls yet.") + "</p>";
	}
	return (
		'<ul class="call-history">' +
		[...referral.calls]
			.reverse()
			.map(
				(call) =>
					"<li><strong>" +
					frappe.utils.escape_html(
						frappe.datetime.str_to_user(call.followup_date) || ""
					) +
					"</strong> " +
					frappe.utils.escape_html(call.summary || "") +
					"</li>"
			)
			.join("") +
		"</ul>"
	);
}

function open_follow_up_dialog(referral) {
	const dialog = new frappe.ui.Dialog({
		title: __("Follow Up: {0}", [referral.patient_name || referral.patient]),
		fields: [
			{
				fieldname: "call_history",
				fieldtype: "HTML",
				options:
					'<div class="helpline-call-history"><div class="text-muted small">' +
					__("Referred to {0}", [frappe.utils.escape_html(referral.referred_to || "")]) +
					"</div>" +
					format_call_history(referral) +
					"</div>",
			},
			{
				fieldname: "summary",
				fieldtype: "Small Text",
				label: __("Follow Up Summary"),
				reqd: 1,
			},
			{
				fieldname: "status",
				fieldtype: "Select",
				label: __("Status"),
				options: [
					{ value: "In Progress", label: __("In Progress") },
					{ value: "Completed", label: __("Completed") },
					{ value: "Lost", label: __("Lost") },
				],
				default: "In Progress",
			},
			{
				fieldname: "next_followup_date",
				fieldtype: "Date",
				label: __("Next Follow Up Date"),
				depends_on: "eval:doc.status == 'In Progress'",
				mandatory_depends_on: "eval:doc.status == 'In Progress'",
			},
			{
				fieldname: "required_action_from",
				fieldtype: "Select",
				label: __("Required Action From"),
				options: ["None", "Programme", "Clinic"],
				default: referral.required_action_from || "None",
			},
		],
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			await frappe.call({
				method: "bandhu_app.bandhu_app.page.referral_follow_up.referral_follow_up.log_follow_up",
				args: { referral: referral.name, ...values },
			});
			dialog.hide();
			frappe.show_alert({ message: __("Follow up saved"), indicator: "green" });
			await load_follow_up_list();
		},
	});
	dialog.show();
}

async function load_follow_up_list() {
	const response = await frappe.call({
		method: "bandhu_app.bandhu_app.page.referral_follow_up.referral_follow_up.get_follow_up_list",
	});
	const data = response.message || { referrals: [], capped: false };

	helpline_page.main.html(
		'<div class="helpline-dash">' +
			bandhu.session_ui.format_welcome() +
			format_follow_up_list(data) +
			"</div>"
	);
	helpline_page.main
		.off("click", ".follow-up-btn")
		.on("click", ".follow-up-btn", (event) =>
			open_follow_up_dialog(data.referrals[cint($(event.currentTarget).data("index"))])
		);
}

frappe.pages["referral-follow-up"].on_page_load = function (wrapper) {
	helpline_page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Referral Follow Up"),
		single_column: true,
	});
};

frappe.pages["referral-follow-up"].on_page_show = async function () {
	await frappe.require(SESSION_UI_ASSET);
	bandhu.session_ui.add_refresh_icon(helpline_page, load_follow_up_list);
	await load_follow_up_list();
};
