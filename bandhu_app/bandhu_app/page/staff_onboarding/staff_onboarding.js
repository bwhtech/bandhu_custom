const STAFF_ONBOARDING_CSS =
	".staff-onboarding-dash{--max-w:var(--page-max-width,700px);max-width:var(--max-w);margin:0 auto;padding:0 var(--padding-md);}" +
	".staff-onboarding-dash .onboarding-form{padding:var(--padding-lg);border:1px solid var(--border-color);border-radius:var(--border-radius-md);background:var(--bg-color);}" +
	".staff-onboarding-dash .onboarding-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:var(--padding-md);}" +
	".staff-onboarding-dash .onboarding-grid .form-group{margin-bottom:0;}" +
	".staff-onboarding-dash .onboarding-grid label{font-size:var(--text-sm);color:var(--text-muted);margin-bottom:4px;}" +
	".staff-onboarding-dash .onboarding-actions{margin-top:var(--margin-lg);display:flex;justify-content:flex-end;}" +
	".staff-onboarding-dash .onboarding-result{margin-top:var(--margin-md);padding:var(--padding-md);border-radius:var(--border-radius-md);background:var(--subtle-fg);font-size:var(--text-sm);}" +
	"@media(max-width:768px){" +
	".staff-onboarding-dash{padding:0 var(--padding-sm);}" +
	".staff-onboarding-dash .onboarding-grid{grid-template-columns:1fr;}}";

let formOptions = { roles: [], genders: [] };

function renderSelectField(name, label, optionsKey, required) {
	const options = formOptions[optionsKey] || [];
	const optionHtml = options
		.map(
			(opt) =>
				'<option value="' + frappe.utils.escape_html(opt) + '">' + frappe.utils.escape_html(opt) + "</option>"
		)
		.join("");
	return (
		'<div class="form-group">' +
		"<label>" +
		frappe.utils.escape_html(label) +
		"</label>" +
		'<select class="form-control onboarding-field" data-field="' +
		name +
		'" ' +
		(required ? "required" : "") +
		">" +
		'<option value="">' +
		__("-- Select --") +
		"</option>" +
		optionHtml +
		"</select></div>"
	);
}

function renderTextField(name, label, type, required, attrs) {
	return (
		'<div class="form-group">' +
		"<label>" +
		frappe.utils.escape_html(label) +
		"</label>" +
		'<input type="' +
		type +
		'" class="form-control onboarding-field" data-field="' +
		name +
		'" ' +
		(required ? "required" : "") +
		" " +
		(attrs || "") +
		"></div>"
	);
}

function renderForm(page) {
	const html =
		"<style>" +
		STAFF_ONBOARDING_CSS +
		"</style>" +
		'<div class="staff-onboarding-dash">' +
		'<div class="onboarding-form">' +
		'<div class="onboarding-grid">' +
		renderTextField("first_name", __("First Name"), "text", true) +
		renderTextField("last_name", __("Last Name"), "text", false) +
		renderTextField("email", __("Email"), "email", true) +
		renderTextField("mobile_phone", __("Mobile"), "tel", false, 'inputmode="numeric" maxlength="10"') +
		renderSelectField("role", __("Role"), "roles", true) +
		renderSelectField("gender", __("Gender"), "genders", false) +
		"</div>" +
		'<div class="onboarding-actions">' +
		'<button class="btn btn-primary btn-lg onboarding-submit">' +
		__("Create Account") +
		"</button>" +
		"</div>" +
		'<div class="onboarding-result" style="display:none;"></div>' +
		"</div></div>";

	page.main.html(html);
	page.main.off("click", ".onboarding-submit").on("click", ".onboarding-submit", () => submitOnboarding(page));
}

function readFormValues(page) {
	const values = {};
	page.main.find(".onboarding-field").each(function () {
		values[$(this).data("field")] = $(this).val();
	});
	return values;
}

async function submitOnboarding(page) {
	const values = readFormValues(page);

	if (!values.first_name || !values.first_name.trim()) {
		frappe.msgprint(__("First name is required."));
		return;
	}
	if (!values.email || !values.email.trim()) {
		frappe.msgprint(__("Email is required."));
		return;
	}
	if (!values.role) {
		frappe.msgprint(__("Please select a role."));
		return;
	}
	if (values.mobile_phone && !/^\d{10}$/.test(values.mobile_phone.trim())) {
		frappe.msgprint(__("Mobile number must be 10 digits."));
		return;
	}

	const args = {
		first_name: values.first_name.trim(),
		email: values.email.trim(),
		role: values.role,
	};
	if (values.last_name) args.last_name = values.last_name.trim();
	if (values.mobile_phone) args.mobile_phone = values.mobile_phone.trim();
	if (values.gender) args.gender = values.gender;

	frappe.dom.freeze();
	let result;
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.staff_onboarding.staff_onboarding.provision_staff_member",
			args,
		});
		result = r.message;
	} catch (e) {
		return;
	} finally {
		frappe.dom.unfreeze();
	}

	if (!result) return;

	const resultBox = page.main.find(".onboarding-result");
	const emailLine = result.email_sent
		? __("A set-password email has been sent to {0}.", [frappe.utils.escape_html(values.email.trim())])
		: __("Account created, but the set-password email could not be sent. Set a password manually.");
	resultBox.show().html(
		"<strong>" +
			__("Account created.") +
			"</strong><br>" +
			frappe.utils.escape_html(result.user) +
			" &middot; " +
			frappe.utils.escape_html(result.practitioner) +
			"<br>" +
			emailLine
	);
	page.main.find(".onboarding-field").val("");
}

async function loadDashboard(page) {
	let optionsResult;
	try {
		optionsResult = await frappe.call({
			method: "bandhu_app.bandhu_app.page.staff_onboarding.staff_onboarding.get_form_options",
		});
	} catch (e) {
		return;
	}
	formOptions = optionsResult.message || formOptions;
	renderForm(page);
}

frappe.pages["staff-onboarding"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Onboard New Staff Member"),
		single_column: true,
	});

	loadDashboard(page);
};
