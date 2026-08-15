const DOCTOR_CSS =
	".doctor-dash{--max-w:var(--page-max-width,1000px);max-width:var(--max-w);margin:0 auto;padding:0 var(--padding-md);}" +
	".doctor-dash .empty-state{display:flex;flex-direction:column;align-items:center;padding:var(--padding-2xl) var(--padding-md);border:1px solid var(--border-color);border-radius:var(--border-radius-md);color:var(--text-muted);background:var(--bg-color);}" +
	".doctor-dash .upcoming-card{margin-top:var(--margin-lg);border:1px solid var(--border-color);border-radius:var(--border-radius-md);background:var(--bg-color);padding:var(--padding-md);}" +
	".doctor-dash .upcoming-title{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--heading-color);margin-bottom:var(--margin-sm);}" +
	".doctor-dash .upcoming-row{display:flex;gap:var(--padding-md);justify-content:space-between;padding:6px 0;font-size:var(--text-sm);border-bottom:1px solid var(--border-color);}" +
	".doctor-dash .upcoming-row:last-child{border-bottom:none;}" +
	".doctor-dash .upcoming-date{font-weight:var(--weight-semibold);white-space:nowrap;}" +
	".doctor-dash .upcoming-site{flex:1;color:var(--text-muted);}" +
	".doctor-dash .upcoming-time{color:var(--text-muted);white-space:nowrap;}" +
	".doctor-dash .table-wrap{overflow:auto;border:1px solid var(--table-border-color);border-radius:var(--border-radius-md);margin-top:var(--margin-sm);}" +
	".doctor-dash .table{margin-bottom:0;min-width:560px;}" +
	".doctor-dash .table thead{position:sticky;top:0;z-index:1;}" +
	".doctor-dash .table th{background:var(--subtle-fg);padding:8px 12px;font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--heading-color);white-space:nowrap;border-bottom:1px solid var(--table-border-color);}" +
	".doctor-dash .table td{padding:10px 12px;vertical-align:middle;border-bottom:1px solid var(--table-border-color);}" +
	".doctor-dash .table tbody tr:last-child td{border-bottom:none;}" +
	".doctor-queue-row{cursor:pointer;}" +
	".doctor-dash .queue-head{font-size:var(--text-lg);font-weight:var(--weight-semibold);color:var(--heading-color);margin:0;}" +
	".doctor-dash .queue-meta{font-weight:var(--weight-regular);font-size:var(--text-base);color:var(--text-muted);}" +
	".doctor-dash .queue-section{margin-bottom:var(--margin-2xl);}" +
	".doctor-dash .queue-section:last-child{margin-bottom:0;}" +
	".doctor-dash .session-bar{display:flex;align-items:center;gap:var(--padding-sm);flex-wrap:wrap;padding:0 0 var(--padding-lg) 0;font-size:var(--text-sm);color:var(--text-muted);}" +
	".history-badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:var(--border-radius-full);font-size:var(--text-xs);font-weight:var(--weight-medium);white-space:nowrap;cursor:default;}" +
	".history-badge.clickable{cursor:pointer;}" +
	".history-badge.first-visit{background:var(--bg-green);color:var(--text-on-green);}" +
	".history-badge.repeat{background:var(--subtle-fg);color:var(--text-color);}" +
	".history-expand-indicator{display:inline-flex;margin-left:2px;font-size:10px;color:inherit;opacity:0.5;transition:transform 0.15s;}" +
	".history-expand-indicator.expanded{transform:rotate(180deg);}" +
	".history-list{list-style:none;margin:6px 0 0 0;padding:0;font-size:var(--text-sm);}" +
	".history-list li{padding:6px 10px;margin:3px 0;background:var(--bg-color);border:1px solid var(--border-color);border-radius:var(--border-radius);}" +
	".history-list li:first-child{margin-top:0;}" +
	".history-list li:last-child{margin-bottom:0;}" +
	".history-list a{color:var(--text-color);text-decoration:none;cursor:pointer;display:block;}" +
	".history-list a:hover{color:var(--primary-color);text-decoration:underline;}" +
	".history-cell{vertical-align:top;min-width:140px;}" +
	".clinical-cell{vertical-align:top;min-width:160px;font-size:var(--text-xs);color:var(--text-muted);}" +
	".clinical-cell .pending{color:var(--yellow-600);}" +
	".doctor-action-btns{display:flex;flex-wrap:wrap;gap:6px;}" +
	".doctor-action-btn{white-space:nowrap;}" +
	".detail-row{display:flex;justify-content:space-between;gap:12px;padding:4px 0;border-bottom:1px solid var(--border-color);font-size:var(--text-sm);}" +
	".detail-row span:first-child{color:var(--text-muted);}" +
	"@media(max-width:768px){" +
	".doctor-dash{padding:0 var(--padding-sm);}" +
	".doctor-dash .table{min-width:400px;}" +
	".doctor-dash .table td,.doctor-dash .table th{padding:8px 10px;}" +
	"}";

const TEST_OPTIONS = ["Malaria", "Dengue", "Leptospirosis", "Hb", "GRBS"].map((name) => ({
	label: name,
	value: name,
}));

let encountersByName = {};
let doctorSession = null;

async function getPatientHistory(patient) {
	const r = await frappe.call({
		method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_patient_history",
		args: { patient },
	});
	return r.message || [];
}

async function loadDashboard(page) {
	frappe.dom.freeze();
	let status;
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_session_status",
		});
		status = r.message || {};
	} catch (e) {
		return;
	} finally {
		frappe.dom.unfreeze();
	}

	if (!status.has_session) {
		doctorSession = null;
		renderNoSession(page, status.message, await getUpcomingSessions());
		return;
	}

	doctorSession = status;
	await loadQueues(page);
}

function renderNoSession(page, message, upcoming) {
	page.main.html(
		"<style>" +
			DOCTOR_CSS +
			"</style>" +
			'<div class="doctor-dash">' +
			renderWelcome() +
			'<div class="empty-state">' +
			'<i class="fa fa-calendar-o" style="font-size:32px;margin-bottom:10px;opacity:0.4;"></i>' +
			'<span style="font-size:var(--text-sm);">' +
			frappe.utils.escape_html(message || __("No session available.")) +
			"</span></div>" +
			renderUpcomingSessions(upcoming) +
			"</div>"
	);
}

async function getUpcomingSessions() {
	try {
		const response = await frappe.call({
			method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_upcoming_sessions",
		});
		return (response && response.message) || [];
	} catch (e) {
		// The upcoming list is informational; failing to load it must not blank the page.
		return [];
	}
}

function renderUpcomingSessions(sessions) {
	if (!sessions || !sessions.length) return "";

	const rows = sessions
		.map(
			(session) =>
				'<div class="upcoming-row">' +
				'<span class="upcoming-date">' +
				frappe.utils.escape_html(frappe.datetime.str_to_user(session.date)) +
				"</span>" +
				'<span class="upcoming-site">' +
				frappe.utils.escape_html(session.site || "") +
				"</span>" +
				'<span class="upcoming-time">' +
				frappe.utils.escape_html(formatPlannedWindow(session)) +
				"</span></div>"
		)
		.join("");

	return (
		'<div class="upcoming-card"><div class="upcoming-title">' +
		__("Your Upcoming Sessions") +
		"</div>" +
		rows +
		"</div>"
	);
}

function formatPlannedWindow(session) {
	if (!session.planned_start_time) return "";
	const start = formatClockTime(session.planned_start_time);
	return session.planned_end_time
		? start + " - " + formatClockTime(session.planned_end_time)
		: start;
}

// A Time field arrives as "9:30:00", not "09:30:00", so it cannot simply be truncated.
function formatClockTime(value) {
	const [hours, minutes] = String(value).split(":");
	return hours.padStart(2, "0") + ":" + (minutes || "00").padStart(2, "0");
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

async function loadQueues(page) {
	frappe.dom.freeze();
	let active, completed;
	try {
		const [activeResult, completedResult] = await Promise.all([
			frappe.call({ method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_registered_patients" }),
			frappe.call({ method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_completed_patients" }),
		]);
		active = activeResult.message || [];
		completed = completedResult.message || [];

		const patients = [...new Set([...active, ...completed].map((p) => p.patient).filter(Boolean))];
		const histories = await Promise.all(patients.map((patient) => getPatientHistory(patient)));
		const historyByPatient = Object.fromEntries(patients.map((patient, i) => [patient, histories[i]]));

		active = active.map((p) => ({ ...p, history: historyByPatient[p.patient] || [] }));
		completed = completed.map((p) => ({ ...p, history: historyByPatient[p.patient] || [] }));
	} catch (e) {
		return;
	} finally {
		frappe.dom.unfreeze();
	}

	encountersByName = Object.fromEntries([...active, ...completed].map((p) => [p.name, p]));
	renderDashboard(page, active, completed);
}

function renderDashboard(page, active, completed) {
	const html =
		"<style>" +
		DOCTOR_CSS +
		"</style>" +
		'<div class="doctor-dash">' +
		renderWelcome() +
		(doctorSession ? renderSessionInfo(doctorSession) : "") +
		renderQueue(__("Active Patients"), active, true) +
		renderQueue(__("Completed Today"), completed, false) +
		"</div>";
	page.main.html(html);

	page.main.off("click");

	page.main.on("click", ".doctor-queue-row", function () {
		frappe.set_route("Form", "Patient Encounter", $(this).data("name"));
	});

	page.main.on("click", ".history-badge.clickable", function (e) {
		e.stopPropagation();
		const target = $(this).siblings(".history-list");
		const indicator = $(this).find(".history-expand-indicator");
		if (target.length) {
			target.toggle();
			indicator.toggleClass("expanded");
		}
	});

	page.main.on("click", ".history-list a", function (e) {
		e.stopPropagation();
		frappe.set_route("Form", "Patient Encounter", $(this).data("name"));
	});

	page.main.on("click", ".doctor-action-btn", function (e) {
		e.stopPropagation();
		const encounter = $(this).data("encounter");
		const action = $(this).data("action");
		dispatchDoctorAction(page, encounter, action);
	});
}

function dispatchDoctorAction(page, encounter, action) {
	switch (action) {
		case "details":
			openDetailsDialog(encounter);
			break;
		case "order_test":
			openOrderTestDialog(page, encounter);
			break;
		case "prescribe":
			openPrescribeDialog(page, encounter);
			break;
		case "complete":
			openCompleteDialog(page, encounter);
			break;
	}
}

function renderWelcome() {
	return (
		'<div style="padding:var(--padding-lg) 0 var(--padding-xl) 0;">' +
		"<h3 style='font-size:var(--text-2xl);font-weight:var(--weight-semibold);color:var(--heading-color);margin:0;'>" +
		__("Welcome, {0}", [frappe.user_info().fullname]) +
		"</h3></div>"
	);
}

async function openDetailsDialog(encounter) {
	const row = encountersByName[encounter];
	if (!row) return;

	frappe.dom.freeze();
	let patient;
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_patient_registration_details",
			args: { encounter },
		});
		patient = r.message || {};
	} catch (e) {
		return;
	} finally {
		frappe.dom.unfreeze();
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Patient Details"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "details_html" }],
	});
	dialog.fields_dict.details_html.$wrapper.html(renderPatientDetailsHtml(patient, row));
	dialog.show();
}

function detailRow(label, value) {
	if (value === null || value === undefined || value === "") return "";
	return (
		'<div class="detail-row"><span>' +
		frappe.utils.escape_html(label) +
		"</span><span>" +
		frappe.utils.escape_html(String(value)) +
		"</span></div>"
	);
}

function renderPatientDetailsHtml(patient, row) {
	const registration =
		detailRow(__("Clinic ID"), patient.custom_bandhu_id) +
		detailRow(__("ABHA ID"), patient.custom_abha_id) +
		detailRow(__("Mobile"), patient.mobile) +
		detailRow(__("Date of Birth"), patient.dob) +
		detailRow(__("Height (m)"), patient.custom_height_m) +
		detailRow(__("Weight (kg)"), patient.custom_weight_kg) +
		detailRow(__("BMI"), patient.custom_bmi) +
		detailRow(__("Temperature"), patient.custom_temperature) +
		detailRow(__("Native State"), patient.custom_native_state) +
		detailRow(__("Native District"), patient.custom_native_district) +
		detailRow(__("Sector of Employment"), patient.custom_sector_of_employment) +
		detailRow(__("Company"), patient.custom_name_of_company);

	const tests = (row.tests || [])
		.map((t) => {
			const result = t.result_type
				? frappe.utils.escape_html(t.result_type) + (t.result_value ? " (" + frappe.utils.escape_html(t.result_value) + ")" : "")
				: '<span class="pending">' + __("pending") + "</span>";
			return (
				"<li>" +
				frappe.utils.escape_html(t.test_name) +
				" -- " +
				result +
				(t.notes ? "<br><small>" + frappe.utils.escape_html(t.notes) + "</small>" : "") +
				"</li>"
			);
		})
		.join("");

	const prescriptions = (row.prescriptions || [])
		.map((p) => {
			const meta = [p.dosage_frequency, p.duration_days ? p.duration_days + "d" : null, p.quantity ? "x" + p.quantity : null]
				.filter(Boolean)
				.join(" ");
			return (
				"<li>" +
				frappe.utils.escape_html(p.medicines) +
				(meta ? " (" + frappe.utils.escape_html(meta) + ")" : "") +
				(p.dispensed ? " -- " + __("Dispensed") : "") +
				(p.instructions ? "<br><small>" + frappe.utils.escape_html(p.instructions) + "</small>" : "") +
				"</li>"
			);
		})
		.join("");

	const diagnosis = (row.diagnosis || [])
		.map(
			(d) =>
				"<li>" +
				frappe.utils.escape_html(d.diagnosis_name) +
				(d.notes ? " -- " + frappe.utils.escape_html(d.notes) : "") +
				"</li>"
		)
		.join("");

	return (
		"<h5>" +
		__("Registration Details") +
		"</h5>" +
		registration +
		(tests ? "<h5 style='margin-top:16px;'>" + __("Tests") + "</h5><ul>" + tests + "</ul>" : "") +
		(prescriptions ? "<h5 style='margin-top:16px;'>" + __("Prescriptions") + "</h5><ul>" + prescriptions + "</ul>" : "") +
		(diagnosis ? "<h5 style='margin-top:16px;'>" + __("Diagnosis") + "</h5><ul>" + diagnosis + "</ul>" : "")
	);
}

function openOrderTestDialog(page, encounter) {
	const dialog = new frappe.ui.Dialog({
		title: __("Order Tests"),
		fields: [
			{
				fieldtype: "MultiCheck",
				fieldname: "tests",
				label: __("Tests"),
				options: TEST_OPTIONS,
				columns: 2,
			},
			{ fieldtype: "Small Text", fieldname: "notes", label: __("Instructions for Nurse") },
		],
		primary_action_label: __("Order Tests"),
		primary_action: async (values) => {
			if (!values.tests || !values.tests.length) {
				frappe.msgprint(__("Select at least one test."));
				return;
			}
			dialog.hide();
			await submitDoctorAction(page, "order_test", {
				encounter,
				tests: values.tests,
				notes: values.notes,
			});
		},
	});
	dialog.show();
}

function openPrescribeDialog(page, encounter) {
	const dialog = new frappe.ui.Dialog({
		title: __("Prescribe Medicine"),
		size: "large",
		fields: [
			{
				fieldtype: "Table",
				fieldname: "prescriptions",
				label: __("Medicines"),
				cannot_add_rows: false,
				in_place_edit: false,
				reqd: 1,
				fields: [
					{
						fieldtype: "Link",
						fieldname: "medicines",
						options: "Item",
						label: __("Medicine"),
						in_list_view: 1,
						reqd: 1,
						get_query: () => ({ filters: { item_group: "Drug" } }),
					},
					{
						fieldtype: "Select",
						fieldname: "dosage_frequency",
						label: __("Frequency"),
						options: "\nOD\nBD\nTID\nQID",
						in_list_view: 1,
					},
					{ fieldtype: "Int", fieldname: "duration_days", label: __("Days"), in_list_view: 1 },
					{ fieldtype: "Int", fieldname: "quantity", label: __("Qty"), in_list_view: 1 },
					{ fieldtype: "Small Text", fieldname: "instructions", label: __("Instructions") },
				],
				data: [],
			},
		],
		primary_action_label: __("Prescribe"),
		primary_action: async (values) => {
			const rows = (values.prescriptions || []).filter((r) => r.medicines);
			if (!rows.length) {
				frappe.msgprint(__("Add at least one medicine."));
				return;
			}
			dialog.hide();
			await submitDoctorAction(page, "prescribe_medicine", { encounter, prescriptions: rows });
		},
	});
	dialog.show();
}

function openCompleteDialog(page, encounter) {
	const dialog = new frappe.ui.Dialog({
		title: __("Mark Complete"),
		fields: [
			{ fieldtype: "Data", fieldname: "diagnosis", label: __("Diagnosis (optional)") },
			{ fieldtype: "Small Text", fieldname: "clinical_notes", label: __("Clinical Notes (optional)") },
		],
		primary_action_label: __("Mark Complete"),
		primary_action: async (values) => {
			dialog.hide();
			await submitDoctorAction(page, "complete_encounter", {
				encounter,
				diagnosis: values.diagnosis,
				clinical_notes: values.clinical_notes,
			});
		},
	});
	dialog.show();
}

async function submitDoctorAction(page, method, args) {
	frappe.dom.freeze();
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form." + method,
			args,
		});
		if (r.message && r.message.success) {
			frappe.show_alert({ message: __("Saved"), indicator: "green" });
			await loadQueues(page);
		}
	} catch (e) {
	} finally {
		frappe.dom.unfreeze();
	}
}

function actionButton(encounterName, action, label) {
	return (
		'<button type="button" class="btn btn-xs btn-default doctor-action-btn" data-encounter="' +
		frappe.utils.escape_html(encounterName) +
		'" data-action="' +
		action +
		'">' +
		frappe.utils.escape_html(label) +
		"</button>"
	);
}

function renderActionButtons(p) {
	const buttons = [actionButton(p.name, "details", __("Details"))];

	if (p.custom_workflow_state === "Waiting for Doctor") {
		buttons.push(actionButton(p.name, "order_test", __("Order Test")));
		buttons.push(actionButton(p.name, "prescribe", __("Prescribe Medicine")));
		buttons.push(actionButton(p.name, "complete", __("Mark Complete")));
	} else if (p.custom_workflow_state === "Awaiting Doctor Review") {
		buttons.push(actionButton(p.name, "prescribe", __("Prescribe Medicine")));
		buttons.push(actionButton(p.name, "complete", __("Mark Complete")));
	}

	return '<div class="doctor-action-btns">' + buttons.join("") + "</div>";
}

function renderClinicalSummary(p) {
	const parts = [];
	if (p.tests && p.tests.length) {
		const done = p.tests.filter((t) => t.result_type).length;
		parts.push(done === p.tests.length ? p.tests.length + " " + __("test(s) done") : done + "/" + p.tests.length + " " + __("test(s) done"));
	}
	if (p.prescriptions && p.prescriptions.length) {
		const dispensed = p.prescriptions.filter((m) => m.dispensed).length;
		parts.push(
			dispensed === p.prescriptions.length
				? p.prescriptions.length + " " + __("medicine(s) dispensed")
				: p.prescriptions.length + " " + __("medicine(s) prescribed")
		);
	}
	if (!parts.length) return "<span class='pending'>" + __("Nothing recorded yet") + "</span>";
	return parts.map(frappe.utils.escape_html).join("<br>");
}

function renderQueue(title, patients, actionable) {
	const count = '<span class="queue-meta"> (' + patients.length + ")</span>";

	if (!patients.length) {
		return (
			'<div class="queue-section">' +
			"<h4 class='queue-head'>" +
			frappe.utils.escape_html(title) +
			count +
			"</h4>" +
			'<div class="empty-state">' +
			'<i class="fa fa-inbox" style="font-size:24px;margin-bottom:8px;opacity:0.4;"></i>' +
			'<span style="font-size:var(--text-sm);">' +
			__("No patients.") +
			"</span>" +
			"</div></div>"
		);
	}

	const rows = patients
		.map((p) => {
			const total = p.history.length;
			const isFirst = total <= 1;
			const badgeClass = isFirst ? "first-visit" : "repeat clickable";
			const badgeLabel = isFirst ? __("First Visit") : __("Repeat Patient") + " &bull; " + total + " " + __("Visits");
			const expandIndicator = isFirst
				? ""
				: '<span class="history-expand-indicator"><i class="fa fa-chevron-down"></i></span>';

			let historyList = "";
			if (!isFirst) {
				const items = p.history
					.map((h) => {
						const d = frappe.datetime.str_to_user(h.encounter_date);
						return "<li><a data-name='" + frappe.utils.escape_html(h.name) + "'>" + frappe.utils.escape_html(d) + "</a></li>";
					})
					.join("");
				historyList = '<ul class="history-list" style="display:none;">' + items + "</ul>";
			}

			return (
				'<tr class="doctor-queue-row" data-name="' +
				frappe.utils.escape_html(p.name) +
				'">' +
				"<td>" +
				frappe.utils.escape_html(p.patient_name || "") +
				"</td>" +
				"<td>" +
				frappe.utils.escape_html(p.patient_age || "") +
				"</td>" +
				"<td>" +
				frappe.utils.escape_html(p.patient_sex || "") +
				"</td>" +
				'<td class="history-cell">' +
				'<span class="history-badge ' +
				badgeClass +
				'" data-patient="' +
				frappe.utils.escape_html(p.patient) +
				'">' +
				badgeLabel +
				expandIndicator +
				"</span>" +
				historyList +
				"</td>" +
				'<td class="clinical-cell">' +
				renderClinicalSummary(p) +
				"</td>" +
				"<td>" +
				renderActionButtons(p) +
				"</td>" +
				"</tr>"
			);
		})
		.join("");

	return (
		'<div class="queue-section">' +
		"<h4 class='queue-head'>" +
		frappe.utils.escape_html(title) +
		count +
		"</h4>" +
		'<div class="table-wrap">' +
		'<table class="table">' +
		"<thead><tr>" +
		"<th>" +
		__("Patient Name") +
		"</th>" +
		"<th>" +
		__("Age") +
		"</th>" +
		"<th>" +
		__("Sex") +
		"</th>" +
		"<th>" +
		__("History") +
		"</th>" +
		"<th>" +
		__("Clinical") +
		"</th>" +
		"<th>" +
		__("Actions") +
		"</th>" +
		"</tr></thead>" +
		"<tbody>" +
		rows +
		"</tbody>" +
		"</table></div></div>"
	);
}

frappe.pages["doctor-form"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Doctor"),
		single_column: true,
	});

	page.set_secondary_action(__("Refresh"), () => loadDashboard(page));
	page.set_primary_action(__("My Schedule"), () => frappe.set_route("my-schedule"), "calendar");

	loadDashboard(page);
};
