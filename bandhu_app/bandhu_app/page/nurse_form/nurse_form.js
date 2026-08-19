let nurseSession = null;
let encountersByName = {};

async function loadDashboard(page) {
	frappe.dom.freeze();
	let data;
	try {
		const response = await frappe.call({
			method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_session_status",
		});
		data = response.message || {};
	} finally {
		frappe.dom.unfreeze();
	}

	if (!data.has_session) {
		page.main.html(
			'<div class="nurse-dash">' +
				renderWelcome() +
				'<div class="empty-state">' +
				'<i class="fa fa-calendar-o empty-state-icon"></i>' +
				'<span class="empty-state-text">' +
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
			'<div class="nurse-dash">' +
				renderWelcome() +
				renderSessionInfo(data) +
				'<div class="start-session-bar">' +
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
			'<div class="nurse-dash">' +
				renderWelcome() +
				renderSessionInfo(data) +
				'<div class="empty-state">' +
				'<i class="fa fa-check-circle empty-state-icon done"></i>' +
				'<span class="empty-state-text">' +
				__("Session completed. Great work!") +
				"</span></div></div>"
		);
	}
}

async function startSession(page) {
	frappe.dom.freeze();
	try {
		await frappe.call({
			method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.start_session",
			args: { session_name: nurseSession.session_name },
		});
	} finally {
		frappe.dom.unfreeze();
	}

	frappe.show_alert({ message: __("Session started"), indicator: "green" });
	await loadDashboard(page);
}

function endSession(page) {
	frappe.confirm(__("End the current session?"), async () => {
		frappe.dom.freeze();
		try {
			await frappe.call({
				method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.end_session",
				args: { session_name: nurseSession.session_name },
			});
		} finally {
			frappe.dom.unfreeze();
		}

		frappe.show_alert({ message: __("Session ended"), indicator: "green" });
		await loadDashboard(page);
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
	} finally {
		frappe.dom.unfreeze();
	}

	const testRows = tests.message || [];
	const medicineRows = medicines.message || [];
	const completedRows = completed.message || [];
	encountersByName = Object.fromEntries(
		[...testRows, ...medicineRows, ...completedRows].map((encounter) => [
			encounter.name,
			encounter,
		])
	);

	page.main.html(
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

	page.main.on("click", ".nurse-action-btn", function (event) {
		event.stopPropagation();
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
		'<div class="welcome"><h3>' +
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
	} catch (error) {
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
	const runningClass = session.status === "In Progress" ? " running" : "";
	return (
		'<div class="session-bar">' +
		'<i class="fa fa-hospital-o"></i> ' +
		frappe.utils.escape_html(session.clinic || "") +
		'<span class="session-sep">|</span>' +
		'<i class="fa fa-map-marker"></i> ' +
		frappe.utils.escape_html(session.site || "") +
		'<span class="session-sep">|</span>' +
		'<i class="fa fa-circle session-dot' +
		runningClass +
		'"></i> ' +
		frappe.utils.escape_html(session.status) +
		"</div>"
	);
}

function renderEndSessionButton() {
	return (
		'<div class="end-session-bar">' +
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
		const response = await frappe.call({
			method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_patient_registration_details",
			args: { encounter },
		});
		patient = response.message || {};
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
		.map((test) => {
			const result = test.result_type
				? frappe.utils.escape_html(test.result_type) +
				  (test.result_value
						? " (" + frappe.utils.escape_html(test.result_value) + ")"
						: "")
				: __("pending");
			return (
				"<li>" +
				frappe.utils.escape_html(test.test_name) +
				" -- " +
				result +
				(test.notes
					? "<br><small>" + frappe.utils.escape_html(test.notes) + "</small>"
					: "") +
				"</li>"
			);
		})
		.join("");

	const prescriptions = (row.prescriptions || [])
		.map((prescription) => {
			const meta = [
				prescription.dosage_frequency,
				prescription.duration_days ? prescription.duration_days + "d" : null,
				prescription.quantity ? "x" + prescription.quantity : null,
			]
				.filter(Boolean)
				.join(" ");
			return (
				"<li>" +
				frappe.utils.escape_html(prescription.medicines) +
				(meta ? " (" + frappe.utils.escape_html(meta) + ")" : "") +
				(prescription.dispensed ? " -- " + __("Dispensed") : "") +
				(prescription.instructions
					? "<br><small>" +
					  frappe.utils.escape_html(prescription.instructions) +
					  "</small>"
					: "") +
				"</li>"
			);
		})
		.join("");

	return (
		"<h5>" +
		__("Registration Details") +
		"</h5>" +
		registration +
		(tests
			? '<h5 class="detail-heading">' + __("Tests") + "</h5><ul>" + tests + "</ul>"
			: "") +
		(prescriptions
			? '<h5 class="detail-heading">' +
			  __("Prescriptions") +
			  "</h5><ul>" +
			  prescriptions +
			  "</ul>"
			: "")
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
					{
						fieldtype: "Data",
						fieldname: "test_name",
						label: __("Test"),
						in_list_view: 1,
						read_only: 1,
					},
					{
						fieldtype: "Select",
						fieldname: "result_type",
						label: __("Result"),
						options: "\nPositive\nNegative\nValue",
						in_list_view: 1,
					},
					{
						fieldtype: "Data",
						fieldname: "result_value",
						label: __("Value"),
						in_list_view: 1,
					},
					{
						fieldtype: "Small Text",
						fieldname: "notes",
						label: __("Doctor's Notes"),
						read_only: 1,
					},
				],
				data: (row.tests || []).map((test) => ({ ...test })),
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
					{
						fieldtype: "Data",
						fieldname: "medicines",
						label: __("Medicine"),
						in_list_view: 1,
						read_only: 1,
					},
					{
						fieldtype: "Small Text",
						fieldname: "instructions",
						label: __("Instructions"),
						read_only: 1,
					},
					{
						fieldtype: "Check",
						fieldname: "dispensed",
						label: __("Dispensed"),
						in_list_view: 1,
						default: 1,
					},
				],
				data: (row.prescriptions || []).map((prescription) => ({ ...prescription })),
			},
		],
		primary_action_label: __("Complete"),
		primary_action: async (values) => {
			const dispensedRows = (values.prescriptions || [])
				.filter((prescription) => prescription.dispensed)
				.map((prescription) => prescription.name);
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
		await frappe.call({
			method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form." + method,
			args,
		});
	} finally {
		frappe.dom.unfreeze();
	}

	frappe.show_alert({ message: __("Saved"), indicator: "green" });
	await loadQueues(page);
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

function renderQueueActionButtons(encounter, action) {
	const buttons = [actionButton(encounter.name, "details", __("Details"), false)];
	if (action === "test") {
		buttons.push(actionButton(encounter.name, "enter_results", __("Enter Results"), true));
	} else if (action === "medicine") {
		buttons.push(actionButton(encounter.name, "dispense", __("Dispense"), true));
	}
	return '<div class="nurse-action-btns">' + buttons.join("") + "</div>";
}

function renderQueueSection(title, encounters, action) {
	const count = '<span class="queue-meta"> (' + encounters.length + ")</span>";

	if (!encounters.length) {
		return (
			'<div class="queue-section">' +
			'<h4 class="queue-head">' +
			frappe.utils.escape_html(title) +
			count +
			"</h4>" +
			'<div class="empty-state">' +
			'<i class="fa fa-inbox empty-state-icon"></i>' +
			'<span class="empty-state-text">' +
			__("No patients in queue.") +
			"</span>" +
			"</div></div>"
		);
	}

	const rows = encounters
		.map(
			(encounter) =>
				'<tr class="nurse-queue-row" data-name="' +
				frappe.utils.escape_html(encounter.name) +
				'">' +
				"<td>" +
				frappe.utils.escape_html(encounter.patient_name || "") +
				"</td>" +
				"<td>" +
				frappe.utils.escape_html(encounter.patient_age || "") +
				"</td>" +
				"<td>" +
				frappe.utils.escape_html(encounter.patient_sex || "") +
				"</td>" +
				"<td>" +
				renderQueueActionButtons(encounter, action) +
				"</td>" +
				"</tr>"
		)
		.join("");

	return (
		'<div class="queue-section">' +
		'<h4 class="queue-head">' +
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
