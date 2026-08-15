const NURSE_CSS =
	".nurse-dash{--max-w:var(--page-max-width,1000px);max-width:var(--max-w);margin:0 auto;padding:0 var(--padding-md);}" +
	".nurse-dash .upcoming-card{margin-top:var(--margin-lg);border:1px solid var(--border-color);border-radius:var(--border-radius-md);background:var(--bg-color);padding:var(--padding-md);}" +
	".nurse-dash .upcoming-title{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--heading-color);margin-bottom:var(--margin-sm);}" +
	".nurse-dash .upcoming-row{display:flex;gap:var(--padding-md);justify-content:space-between;padding:6px 0;font-size:var(--text-sm);border-bottom:1px solid var(--border-color);}" +
	".nurse-dash .upcoming-row:last-child{border-bottom:none;}" +
	".nurse-dash .upcoming-date{font-weight:var(--weight-semibold);white-space:nowrap;}" +
	".nurse-dash .upcoming-site{flex:1;color:var(--text-muted);}" +
	".nurse-dash .upcoming-time{color:var(--text-muted);white-space:nowrap;}" +
	".nurse-dash .empty-state{display:flex;flex-direction:column;align-items:center;padding:var(--padding-2xl) var(--padding-md);border:1px solid var(--border-color);border-radius:var(--border-radius-md);color:var(--text-muted);background:var(--bg-color);}" +
	".nurse-dash .table-wrap{overflow:auto;border:1px solid var(--table-border-color);border-radius:var(--border-radius-md);margin-top:var(--margin-sm);}" +
	".nurse-dash .table{margin-bottom:0;min-width:480px;}" +
	".nurse-dash .table thead{position:sticky;top:0;z-index:1;}" +
	".nurse-dash .table th{background:var(--subtle-fg);padding:8px 12px;font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--heading-color);white-space:nowrap;border-bottom:1px solid var(--table-border-color);}" +
	".nurse-dash .table td{padding:10px 12px;vertical-align:middle;border-bottom:1px solid var(--table-border-color);}" +
	".nurse-dash .table tbody tr:last-child td{border-bottom:none;}" +
	".nurse-queue-row{cursor:pointer;}" +
	".nurse-dash .queue-head{font-size:var(--text-lg);font-weight:var(--weight-semibold);color:var(--heading-color);margin:0;}" +
	".nurse-dash .queue-meta{font-weight:var(--weight-regular);font-size:var(--text-base);color:var(--text-muted);}" +
	".nurse-dash .queue-section{margin-bottom:var(--margin-2xl);}" +
	".nurse-dash .queue-section:last-child{margin-bottom:0;}" +
	".nurse-dash .session-bar{display:flex;align-items:center;gap:var(--padding-sm);flex-wrap:wrap;padding:0 0 var(--padding-lg) 0;font-size:var(--text-sm);color:var(--text-muted);}" +
	".nurse-action-btns{display:flex;flex-wrap:wrap;gap:6px;}" +
	".nurse-action-btn{white-space:nowrap;}" +
	".detail-row{display:flex;justify-content:space-between;gap:12px;padding:4px 0;border-bottom:1px solid var(--border-color);font-size:var(--text-sm);}" +
	".detail-row span:first-child{color:var(--text-muted);}" +
	"@media(max-width:768px){" +
	".nurse-dash{padding:0 var(--padding-sm);}" +
	".nurse-dash .table{min-width:350px;}" +
	".nurse-dash .table td,.nurse-dash .table th{padding:8px 10px;}}";

let nurseSession = null;
let encountersByName = {};

async function loadDashboard(page) {
	frappe.dom.freeze();
	let data;
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_session_status",
		});
		data = r.message || {};
	} catch (e) {
		return;
	} finally {
		frappe.dom.unfreeze();
	}

	if (!data.has_session) {
		page.main.html(
			"<style>" +
				NURSE_CSS +
				"</style>" +
				'<div class="nurse-dash">' +
				renderWelcome() +
				'<div class="empty-state">' +
				'<i class="fa fa-calendar-o" style="font-size:32px;margin-bottom:10px;opacity:0.4;"></i>' +
				'<span style="font-size:var(--text-sm);">' +
				frappe.utils.escape_html(data.message) +
				"</span></div>" +
				renderUpcomingSessions(await getUpcomingSessions()) +
				"</div>"
		);
		return;
	}

	nurseSession = data;

	if (data.status === "Planned") {
		page.main.html(
			"<style>" +
				NURSE_CSS +
				"</style>" +
				'<div class="nurse-dash">' +
				renderWelcome() +
				renderSessionInfo(data) +
				'<div style="padding:var(--padding-xl) 0;display:flex;justify-content:center;">' +
				'<button class="btn btn-primary btn-lg nurse-start-session">' +
				'<i class="fa fa-play"></i> ' +
				__("Start Session") +
				"</button></div></div>"
		);

		page.main.off("click").on("click", ".nurse-start-session", () => startSession(page));
	} else if (data.status === "In Progress") {
		await loadQueues(page);
	} else if (data.status === "Completed") {
		page.main.html(
			"<style>" +
				NURSE_CSS +
				"</style>" +
				'<div class="nurse-dash">' +
				renderWelcome() +
				renderSessionInfo(data) +
				'<div class="empty-state">' +
				'<i class="fa fa-check-circle" style="font-size:32px;color:var(--green-500);margin-bottom:10px;"></i>' +
				'<span style="font-size:var(--text-sm);">' +
				__("Session completed. Great work!") +
				"</span></div></div>"
		);
	}
}

async function startSession(page) {
	frappe.dom.freeze();
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.start_session",
			args: { session_name: nurseSession.session_name },
		});
		if (r.message && r.message.success) {
			frappe.show_alert({ message: __("Session started"), indicator: "green" });
			await loadDashboard(page);
		}
	} catch (e) {
		frappe.show_alert({ message: __("Failed to start session"), indicator: "red" });
	} finally {
		frappe.dom.unfreeze();
	}
}

function endSession(page) {
	frappe.confirm(__("End the current session?"), async () => {
		frappe.dom.freeze();
		try {
			const r = await frappe.call({
				method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.end_session",
				args: { session_name: nurseSession.session_name },
			});
			if (r.message && r.message.success) {
				frappe.show_alert({ message: __("Session ended"), indicator: "green" });
				await loadDashboard(page);
			}
		} catch (e) {
			frappe.show_alert({ message: __("Failed to end session"), indicator: "red" });
		} finally {
			frappe.dom.unfreeze();
		}
	});
}

async function loadQueues(page) {
	frappe.dom.freeze();
	const sessionName = nurseSession.session_name;
	let tests, medicines, completed;
	try {
		[tests, medicines, completed] = await Promise.all([
			frappe.call({
				method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_patients_for_tests",
				args: { session_name: sessionName },
			}),
			frappe.call({
				method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_patients_for_medicines",
				args: { session_name: sessionName },
			}),
			frappe.call({
				method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_completed_patients",
				args: { session_name: sessionName },
			}),
		]);
	} catch (e) {
		return;
	} finally {
		frappe.dom.unfreeze();
	}

	const testRows = tests.message || [];
	const medicineRows = medicines.message || [];
	const completedRows = completed.message || [];
	encountersByName = Object.fromEntries([...testRows, ...medicineRows, ...completedRows].map((p) => [p.name, p]));

	page.main.html(
		"<style>" +
			NURSE_CSS +
			"</style>" +
			'<div class="nurse-dash">' +
			renderWelcome() +
			renderSessionInfo(nurseSession) +
			renderEndSessionButton() +
			renderQueueSection(__("Patients for Tests"), testRows, "test") +
			renderQueueSection(__("Patients for Medicines"), medicineRows, "medicine") +
			renderQueueSection(__("Completed Patients"), completedRows, null) +
			"</div>"
	);

	page.main.off("click");

	page.main.on("click", ".nurse-end-session", () => endSession(page));

	page.main.on("click", ".nurse-queue-row", function () {
		frappe.set_route("Form", "Patient Encounter", $(this).data("name"));
	});

	page.main.on("click", ".nurse-action-btn", function (e) {
		e.stopPropagation();
		const encounter = $(this).data("encounter");
		const action = $(this).data("action");
		dispatchNurseAction(page, encounter, action);
	});
}

function dispatchNurseAction(page, encounter, action) {
	switch (action) {
		case "details":
			openDetailsDialog(encounter);
			break;
		case "enter_results":
			openTestResultsDialog(page, encounter);
			break;
		case "dispense":
			openDispenseDialog(page, encounter);
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

async function getUpcomingSessions() {
	try {
		const response = await frappe.call({
			method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_upcoming_sessions",
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

function renderEndSessionButton() {
	return (
		'<div style="padding:0 0 var(--padding-lg) 0;">' +
		'<button class="btn btn-danger btn-sm nurse-end-session">' +
		'<i class="fa fa-stop"></i> ' +
		__("End Session") +
		"</button></div>"
	);
}

async function openDetailsDialog(encounter) {
	const row = encountersByName[encounter];
	if (!row) return;

	frappe.dom.freeze();
	let patient;
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_patient_registration_details",
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
				: __("pending");
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

	return (
		"<h5>" +
		__("Registration Details") +
		"</h5>" +
		registration +
		(tests ? "<h5 style='margin-top:16px;'>" + __("Tests") + "</h5><ul>" + tests + "</ul>" : "") +
		(prescriptions ? "<h5 style='margin-top:16px;'>" + __("Prescriptions") + "</h5><ul>" + prescriptions + "</ul>" : "")
	);
}

function openTestResultsDialog(page, encounter) {
	const row = encountersByName[encounter];
	if (!row) return;

	const dialog = new frappe.ui.Dialog({
		title: __("Enter Test Results"),
		size: "large",
		fields: [
			{
				fieldtype: "Table",
				fieldname: "results",
				label: __("Tests"),
				cannot_add_rows: true,
				cannot_delete_rows: true,
				in_place_edit: false,
				fields: [
					{ fieldtype: "Data", fieldname: "test_name", label: __("Test"), in_list_view: 1, read_only: 1 },
					{
						fieldtype: "Select",
						fieldname: "result_type",
						label: __("Result"),
						options: "\nPositive\nNegative\nValue",
						in_list_view: 1,
					},
					{ fieldtype: "Data", fieldname: "result_value", label: __("Value"), in_list_view: 1 },
					{ fieldtype: "Small Text", fieldname: "notes", label: __("Doctor's Notes"), read_only: 1 },
				],
				data: (row.tests || []).map((t) => ({ ...t })),
			},
		],
		primary_action_label: __("Save Results"),
		primary_action: async (values) => {
			dialog.hide();
			await submitNurseAction(page, "submit_test_results", {
				encounter,
				results: values.results,
			});
		},
	});
	dialog.show();
}

function openDispenseDialog(page, encounter) {
	const row = encountersByName[encounter];
	if (!row) return;

	const dialog = new frappe.ui.Dialog({
		title: __("Dispense Medicine"),
		size: "large",
		fields: [
			{
				fieldtype: "Table",
				fieldname: "prescriptions",
				label: __("Medicines"),
				cannot_add_rows: true,
				cannot_delete_rows: true,
				in_place_edit: false,
				fields: [
					{ fieldtype: "Data", fieldname: "medicines", label: __("Medicine"), in_list_view: 1, read_only: 1 },
					{ fieldtype: "Small Text", fieldname: "instructions", label: __("Instructions"), read_only: 1 },
					{ fieldtype: "Check", fieldname: "dispensed", label: __("Dispensed"), in_list_view: 1, default: 1 },
				],
				data: (row.prescriptions || []).map((p) => ({ ...p })),
			},
		],
		primary_action_label: __("Complete"),
		primary_action: async (values) => {
			const dispensedRows = (values.prescriptions || []).filter((p) => p.dispensed).map((p) => p.name);
			dialog.hide();
			await submitNurseAction(page, "dispense_medicine", {
				encounter,
				dispensed_rows: dispensedRows,
			});
		},
	});
	dialog.show();
}

async function submitNurseAction(page, method, args) {
	frappe.dom.freeze();
	try {
		const r = await frappe.call({
			method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form." + method,
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

function actionButton(encounterName, action, label, primary) {
	return (
		'<button type="button" class="btn btn-xs ' +
		(primary ? "btn-primary" : "btn-default") +
		' nurse-action-btn" data-encounter="' +
		frappe.utils.escape_html(encounterName) +
		'" data-action="' +
		action +
		'">' +
		frappe.utils.escape_html(label) +
		"</button>"
	);
}

function renderQueueActionButtons(p, action) {
	const buttons = [actionButton(p.name, "details", __("Details"), false)];
	if (action === "test") {
		buttons.push(actionButton(p.name, "enter_results", __("Enter Results"), true));
	} else if (action === "medicine") {
		buttons.push(actionButton(p.name, "dispense", __("Dispense"), true));
	}
	return '<div class="nurse-action-btns">' + buttons.join("") + "</div>";
}

function renderQueueSection(title, patients, action) {
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
			__("No patients in queue.") +
			"</span>" +
			"</div></div>"
		);
	}

	const rows = patients
		.map(
			(p) =>
				'<tr class="nurse-queue-row" data-name="' +
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
				"<td>" +
				renderQueueActionButtons(p, action) +
				"</td>" +
				"</tr>"
		)
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
		__("Actions") +
		"</th>" +
		"</tr></thead>" +
		"<tbody>" +
		rows +
		"</tbody>" +
		"</table></div></div>"
	);
}

frappe.pages["nurse-form"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Nurse"),
		single_column: true,
	});

	page.set_secondary_action(__("Refresh"), () => loadDashboard(page));
	page.set_primary_action(__("My Schedule"), () => frappe.set_route("my-schedule"), "calendar");

	loadDashboard(page);
};
