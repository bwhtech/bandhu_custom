const CAD_CSS =
	".cad-dash{--max-w:var(--page-max-width,900px);max-width:var(--max-w);margin:0 auto;padding:0 var(--padding-md);}" +
	".cad-dash .empty-state{display:flex;flex-direction:column;align-items:center;padding:var(--padding-2xl) var(--padding-md);border:1px solid var(--border-color);border-radius:var(--border-radius-md);color:var(--text-muted);background:var(--bg-color);}" +
	".cad-dash .session-bar{display:flex;align-items:center;gap:var(--padding-sm);flex-wrap:wrap;padding:0 0 var(--padding-lg) 0;font-size:var(--text-sm);color:var(--text-muted);}" +
	".cad-dash .queue-head{font-size:var(--text-lg);font-weight:var(--weight-semibold);color:var(--heading-color);margin:0;}" +
	".cad-dash .queue-meta{font-weight:var(--weight-regular);font-size:var(--text-base);color:var(--text-muted);}" +
	".cad-dash .cad-search-section{margin-bottom:var(--margin-xl);}" +
	".cad-dash .search-row{display:flex;gap:var(--padding-sm);}" +
	".cad-dash .search-row input{flex:1;}" +
	".cad-dash .cad-search-results{margin-top:var(--margin-sm);}" +
	".cad-dash .patient-result-row{display:flex;flex-direction:column;gap:2px;padding:10px 12px;border:1px solid var(--border-color);border-radius:var(--border-radius-md);margin-bottom:6px;cursor:pointer;background:var(--bg-color);}" +
	".cad-dash .patient-result-row:hover{border-color:var(--primary-color);}" +
	".cad-dash .patient-result-row .pr-name{font-weight:var(--weight-semibold);color:var(--heading-color);}" +
	".cad-dash .patient-result-row .pr-meta{font-size:var(--text-xs);color:var(--text-muted);}" +
	".cad-dash .cad-register-section{margin-bottom:var(--margin-xl);}" +
	".cad-dash .cad-register-form{margin-top:var(--margin-sm);padding:var(--padding-lg);border:1px solid var(--border-color);border-radius:var(--border-radius-md);background:var(--bg-color);}" +
	".cad-dash .register-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:var(--padding-md);}" +
	".cad-dash .register-grid .form-group{margin-bottom:0;}" +
	".cad-dash .register-grid label{font-size:var(--text-sm);color:var(--text-muted);margin-bottom:4px;}" +
	".cad-dash .sex-btn-group{display:flex;gap:8px;}" +
	".cad-dash .sex-btn{flex:1;}" +
	".cad-dash .register-actions{margin-top:var(--margin-lg);display:flex;justify-content:flex-end;}" +
	".cad-dash .cad-queue-section{margin-top:var(--margin-xl);}" +
	".cad-dash .table-wrap{overflow:auto;border:1px solid var(--table-border-color);border-radius:var(--border-radius-md);margin-top:var(--margin-sm);max-height:360px;}" +
	".cad-dash .table{margin-bottom:0;min-width:400px;}" +
	".cad-dash .table thead{position:sticky;top:0;z-index:1;}" +
	".cad-dash .table th{background:var(--subtle-fg);padding:8px 12px;font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--heading-color);white-space:nowrap;border-bottom:1px solid var(--table-border-color);}" +
	".cad-dash .table td{padding:10px 12px;vertical-align:middle;border-bottom:1px solid var(--table-border-color);}" +
	".cad-dash .table tbody tr:last-child td{border-bottom:none;}" +
	"@media(max-width:768px){" +
	".cad-dash{padding:0 var(--padding-sm);}" +
	".cad-dash .register-grid{grid-template-columns:1fr;}" +
	".cad-dash .table{min-width:350px;}" +
	".cad-dash .table td,.cad-dash .table th{padding:8px 10px;}}";

let cadSession = null;
let formOptions = { states: [], sectors: [] };

const REGISTER_FIELDS = [
	{ name: "full_name", label: __("Full Name"), type: "text" },
	{ name: "dob", label: __("Date of Birth"), type: "date" },
	{ name: "height_cm", label: __("Height (cm)"), type: "number", attrs: 'min="0" step="0.1" inputmode="decimal"' },
	{ name: "weight_kg", label: __("Weight (kg)"), type: "number", attrs: 'min="0" step="0.1" inputmode="decimal"' },
	{ name: "native_state", label: __("Native State"), type: "select", optionsKey: "states" },
	{ name: "native_district", label: __("Native District"), type: "text" },
	{ name: "occupation", label: __("Occupation / Sector"), type: "select", optionsKey: "sectors" },
	{ name: "company_name", label: __("Company Name"), type: "text" },
	{ name: "mobile", label: __("Mobile"), type: "tel", attrs: 'inputmode="numeric" maxlength="10"' },
	{ name: "abha_id", label: __("ABHA ID"), type: "text" },
];

async function loadDashboard(page) {
	frappe.dom.freeze();
	let statusResult;
	try {
		statusResult = await frappe.call({
			method: "bandhu_app.bandhu_app.page.cad_form.cad_form.get_session_status",
		});
	} catch (e) {
		return;
	} finally {
		frappe.dom.unfreeze();
	}

	const data = statusResult.message || {};

	if (!data.has_session) {
		renderNoSession(page, data);
		return;
	}

	cadSession = data;

	if (data.status === "Completed") {
		renderCompleted(page, data);
		return;
	}

	if (data.status === "Planned") {
		renderWaitingForNurse(page, data);
		return;
	}

	try {
		const optionsResult = await frappe.call({
			method: "bandhu_app.bandhu_app.page.cad_form.cad_form.get_form_options",
		});
		formOptions = optionsResult.message || { states: [], sectors: [] };
	} catch (e) {
	}

	renderFrontDesk(page, data);
}

function renderNoSession(page, data) {
	page.main.html(
		"<style>" +
			CAD_CSS +
			"</style>" +
			'<div class="cad-dash">' +
			renderWelcome() +
			'<div class="empty-state">' +
			'<i class="fa fa-calendar-o" style="font-size:32px;margin-bottom:10px;opacity:0.4;"></i>' +
			'<span style="font-size:var(--text-sm);">' +
			frappe.utils.escape_html(data.message || __("No session available.")) +
			"</span></div></div>"
	);
}

function renderWaitingForNurse(page, data) {
	page.main.html(
		"<style>" +
			CAD_CSS +
			"</style>" +
			'<div class="cad-dash">' +
			renderWelcome() +
			renderSessionInfo(data) +
			'<div class="empty-state">' +
			'<i class="fa fa-hourglass-half" style="font-size:32px;margin-bottom:10px;opacity:0.4;"></i>' +
			'<span style="font-size:var(--text-sm);">' +
			__("Waiting for the nurse to start this clinic session. Patients can't be registered yet.") +
			"</span></div></div>"
	);
}

function renderCompleted(page, data) {
	page.main.html(
		"<style>" +
			CAD_CSS +
			"</style>" +
			'<div class="cad-dash">' +
			renderWelcome() +
			renderSessionInfo(data) +
			'<div class="empty-state">' +
			'<i class="fa fa-check-circle" style="font-size:32px;color:var(--green-500);margin-bottom:10px;"></i>' +
			'<span style="font-size:var(--text-sm);">' +
			__("Session completed. No further patients can be registered.") +
			"</span></div></div>"
	);
}

function renderFrontDesk(page, data) {
	const html =
		"<style>" +
		CAD_CSS +
		"</style>" +
		'<div class="cad-dash">' +
		renderWelcome() +
		renderSessionInfo(data) +
		renderSearchSection() +
		renderRegisterSection() +
		'<div class="cad-queue-section">' +
		"<h4 class='queue-head'>" +
		__("Today's Queue") +
		'<span class="queue-meta cad-queue-count"></span>' +
		"</h4>" +
		'<div class="table-wrap">' +
		'<table class="table">' +
		"<thead><tr>" +
		"<th>" +
		__("Patient") +
		"</th>" +
		"<th>" +
		__("Stage") +
		"</th>" +
		"<th>" +
		__("Status") +
		"</th>" +
		"</tr></thead>" +
		'<tbody class="cad-queue-body"></tbody>' +
		"</table></div></div>" +
		"</div>";

	page.main.html(html);
	bindSearchEvents(page);
	bindRegisterEvents(page);
	loadQueue(page);
}

function renderWelcome() {
	return (
		'<div style="padding:var(--padding-lg) 0 var(--padding-xl) 0;">' +
		"<h3 style='font-size:var(--text-2xl);font-weight:var(--weight-semibold);color:var(--heading-color);margin:0;'>" +
		__("Welcome, {0}", [frappe.user_info().fullname]) +
		"</h3></div>"
	);
}

function renderSessionInfo(session) {
	const statusColor = session.status === "In Progress" ? "var(--green-500)" : "var(--text-muted)";
	return (
		'<div class="session-bar">' +
		'<i class="fa fa-hospital-o"></i> ' +
		frappe.utils.escape_html(session.clinic || "") +
		'<span style="color:var(--border-color);">|</span>' +
		'<i class="fa fa-map-marker"></i> ' +
		frappe.utils.escape_html(session.site || "") +
		'<span style="color:var(--border-color);">|</span>' +
		'<i class="fa fa-circle" style="color:' +
		statusColor +
		';font-size:8px;"></i> ' +
		frappe.utils.escape_html(session.status) +
		"</div>"
	);
}

function renderSearchSection() {
	return (
		'<div class="cad-search-section">' +
		"<h4 class='queue-head' style='margin-bottom:var(--margin-sm);'>" +
		__("Find Existing Patient") +
		"</h4>" +
		'<div class="search-row">' +
		'<input type="text" class="form-control cad-search-input" placeholder="' +
		frappe.utils.escape_html(__("Search by Clinic ID, ABHA ID, Mobile, Name or DOB")) +
		'">' +
		'<button class="btn btn-primary cad-search-btn">' +
		__("Search") +
		"</button>" +
		"</div>" +
		'<div class="cad-search-results"></div>' +
		"</div>"
	);
}

function renderRegisterSection() {
	return (
		'<div class="cad-register-section">' +
		'<button class="btn btn-default cad-register-toggle-btn">' +
		'<i class="fa fa-user-plus"></i> ' +
		__("Register New Patient") +
		"</button>" +
		'<div class="cad-register-form" style="display:none;">' +
		renderRegisterForm() +
		"</div>" +
		"</div>"
	);
}

function renderSelectField(field) {
	const options = formOptions[field.optionsKey] || [];
	const optionHtml = options
		.map(
			(opt) =>
				'<option value="' + frappe.utils.escape_html(opt) + '">' + frappe.utils.escape_html(opt) + "</option>"
		)
		.join("");
	return (
		'<select class="form-control cad-field" data-field="' +
		field.name +
		'">' +
		'<option value="">' +
		__("-- Select --") +
		"</option>" +
		optionHtml +
		"</select>"
	);
}

function renderRegisterForm() {
	const fields = REGISTER_FIELDS.map((field) => {
		const input =
			field.type === "select"
				? renderSelectField(field)
				: '<input type="' +
				  field.type +
				  '" class="form-control cad-field" data-field="' +
				  field.name +
				  '" ' +
				  (field.attrs || "") +
				  ">";
		return (
			'<div class="form-group">' +
			"<label>" +
			frappe.utils.escape_html(field.label) +
			"</label>" +
			input +
			"</div>"
		);
	}).join("");

	const sexGroup =
		'<div class="form-group">' +
		"<label>" +
		__("Sex") +
		"</label>" +
		'<div class="sex-btn-group" data-field="sex">' +
		["Male", "Female", "Other"]
			.map(
				(s) =>
					'<button type="button" class="btn btn-default sex-btn" data-value="' + s + '">' + __(s) + "</button>"
			)
			.join("") +
		"</div></div>";

	return (
		'<div class="register-grid">' +
		fields +
		sexGroup +
		"</div>" +
		'<div class="register-actions">' +
		'<button class="btn btn-primary btn-lg cad-register-submit">' +
		__("Register & Add to Queue") +
		"</button>" +
		"</div>"
	);
}

function bindSearchEvents(page) {
	page.main.off("click", ".cad-search-btn").on("click", ".cad-search-btn", () => searchPatients(page));

	page.main.off("keypress", ".cad-search-input").on("keypress", ".cad-search-input", (e) => {
		if (e.which === 13) searchPatients(page);
	});

	page.main.off("click", ".patient-result-row").on("click", ".patient-result-row", function () {
		const patient = $(this).data("patient");
		frappe.confirm(__("Add this patient to today's queue?"), async () => {
			await addPatientToQueue(page, patient, () => {
				page.main.find(".cad-search-results").empty();
				page.main.find(".cad-search-input").val("");
			});
		});
	});
}

async function searchPatients(page) {
	const query = page.main.find(".cad-search-input").val();
	if (!query || !query.trim()) return;

	frappe.dom.freeze();
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.cad_form.cad_form.search_patient",
			args: { query: query.trim() },
		});
		renderSearchResults(page, r.message || []);
	} catch (e) {
	} finally {
		frappe.dom.unfreeze();
	}
}

function renderSearchResults(page, results) {
	const container = page.main.find(".cad-search-results");
	if (!results.length) {
		container.html(
			'<div class="empty-state"><span style="font-size:var(--text-sm);">' + __("No matching patients.") + "</span></div>"
		);
		return;
	}

	const rows = results
		.map((p) => {
			const meta = [p.custom_bandhu_id, p.sex, p.dob].filter(Boolean).map(frappe.utils.escape_html).join(" &bull; ");
			return (
				'<div class="patient-result-row" data-patient="' +
				frappe.utils.escape_html(p.name) +
				'">' +
				'<span class="pr-name">' +
				frappe.utils.escape_html(p.patient_name || "") +
				"</span>" +
				'<span class="pr-meta">' +
				meta +
				"</span>" +
				"</div>"
			);
		})
		.join("");

	container.html(rows);
}

function bindRegisterEvents(page) {
	page.main.off("click", ".cad-register-toggle-btn").on("click", ".cad-register-toggle-btn", () => {
		page.main.find(".cad-register-form").toggle();
	});

	page.main.off("click", ".sex-btn").on("click", ".sex-btn", function () {
		$(this).siblings(".sex-btn").removeClass("btn-primary active").addClass("btn-default");
		$(this).addClass("btn-primary active").removeClass("btn-default");
	});

	page.main.off("click", ".cad-register-submit").on("click", ".cad-register-submit", () => submitRegistration(page));
}

async function submitRegistration(page) {
	const values = {};
	page.main.find(".cad-field").each(function () {
		values[$(this).data("field")] = $(this).val();
	});
	values.sex = page.main.find(".sex-btn.active").data("value");

	if (!values.full_name || !values.full_name.trim()) {
		frappe.msgprint(__("Full name is required."));
		return;
	}
	if (!values.dob) {
		frappe.msgprint(__("Date of birth is required."));
		return;
	}
	if (!values.sex) {
		frappe.msgprint(__("Please select sex."));
		return;
	}
	if (values.mobile && !/^\d{10}$/.test(values.mobile.trim())) {
		frappe.msgprint(__("Mobile number must be 10 digits."));
		return;
	}
	if (values.height_cm && flt(values.height_cm) < 0) {
		frappe.msgprint(__("Height cannot be negative."));
		return;
	}
	if (values.weight_kg && flt(values.weight_kg) < 0) {
		frappe.msgprint(__("Weight cannot be negative."));
		return;
	}

	const args = {
		full_name: values.full_name.trim(),
		dob: values.dob,
		sex: values.sex,
	};
	if (values.mobile) args.mobile = values.mobile;
	if (values.height_cm) args.height_cm = values.height_cm;
	if (values.weight_kg) args.weight_kg = values.weight_kg;
	if (values.native_state) args.native_state = values.native_state;
	if (values.native_district) args.native_district = values.native_district;
	if (values.occupation) args.occupation = values.occupation;
	if (values.company_name) args.company_name = values.company_name;
	if (values.abha_id) args.abha_id = values.abha_id;

	frappe.dom.freeze();
	let patient;
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.cad_form.cad_form.register_patient",
			args,
		});
		patient = r.message;
	} catch (e) {
		return;
	} finally {
		frappe.dom.unfreeze();
	}

	if (!patient) return;

	await addPatientToQueue(page, patient, () => {
		page.main.find(".cad-register-form").hide();
		page.main.find(".cad-field").val("");
		page.main.find(".sex-btn").removeClass("btn-primary active").addClass("btn-default");
	});
}

async function addPatientToQueue(page, patient, onSuccess) {
	frappe.dom.freeze();
	try {
		await frappe.call({
			method: "bandhu_app.bandhu_app.page.cad_form.cad_form.create_encounter",
			args: { patient, session: cadSession.session_name },
		});
		onSuccess();
		await loadQueue(page);
	} catch (e) {
	} finally {
		frappe.dom.unfreeze();
	}
}

async function loadQueue(page) {
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.cad_form.cad_form.get_today_queue",
			args: { session: cadSession.session_name },
		});
		renderQueueTable(page, r.message || []);
	} catch (e) {
	}
}

function renderQueueTable(page, rows) {
	page.main.find(".cad-queue-count").text(" (" + rows.length + ")");
	const body = page.main.find(".cad-queue-body");

	if (!rows.length) {
		body.html(
			'<tr><td colspan="3" style="text-align:center;color:var(--text-muted);">' + __("No patients in queue yet.") + "</td></tr>"
		);
		return;
	}

	const html = rows
		.map(
			(row) =>
				"<tr>" +
				"<td>" +
				frappe.utils.escape_html(row.patient_name || "") +
				"</td>" +
				"<td>" +
				frappe.utils.escape_html(row.current_stage || "") +
				"</td>" +
				"<td>" +
				frappe.utils.escape_html(row.status || "") +
				"</td>" +
				"</tr>"
		)
		.join("");

	body.html(html);
}

frappe.pages["cad-form"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("CAD Front Desk"),
		single_column: true,
	});

	page.set_secondary_action(__("Refresh"), () => loadDashboard(page));

	loadDashboard(page);
};
