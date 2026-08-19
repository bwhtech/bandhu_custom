const TEST_OPTIONS = ["Malaria", "Dengue", "Leptospirosis", "Hb", "GRBS"].map((name) => ({
	label: name,
	value: name,
}));

let encountersByName = {};
let doctorSession = null;

async function getPatientHistory(patient) {
	const response = await frappe.call({
		method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_patient_history",
		args: { patient },
	});
	return response.message || [];
}

async function loadDashboard(page) {
	frappe.dom.freeze();
	let status;
	try {
		const response = await frappe.call({
			method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_session_status",
		});
		status = response.message || {};
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
		'<div class="doctor-dash">' +
			renderWelcome() +
			'<div class="empty-state">' +
			'<i class="fa fa-calendar-o empty-state-icon"></i>' +
			'<span class="empty-state-text">' +
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

async function loadQueues(page) {
	frappe.dom.freeze();
	let active, completed;
	try {
		const [activeResult, completedResult] = await Promise.all([
			frappe.call({
				method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_registered_patients",
			}),
			frappe.call({
				method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_completed_patients",
			}),
		]);
		active = activeResult.message || [];
		completed = completedResult.message || [];

		const patients = [
			...new Set(
				[...active, ...completed].map((encounter) => encounter.patient).filter(Boolean)
			),
		];
		const histories = await Promise.all(patients.map((patient) => getPatientHistory(patient)));
		const historyByPatient = Object.fromEntries(
			patients.map((patient, index) => [patient, histories[index]])
		);

		active = active.map((encounter) => ({
			...encounter,
			history: historyByPatient[encounter.patient] || [],
		}));
		completed = completed.map((encounter) => ({
			...encounter,
			history: historyByPatient[encounter.patient] || [],
		}));
	} finally {
		frappe.dom.unfreeze();
	}

	encountersByName = Object.fromEntries(
		[...active, ...completed].map((encounter) => [encounter.name, encounter])
	);
	renderDashboard(page, active, completed);
}

function renderDashboard(page, active, completed) {
	const html =
		'<div class="doctor-dash">' +
		renderWelcome() +
		(doctorSession ? renderSessionInfo(doctorSession) : "") +
		renderQueue(__("Active Patients"), active) +
		renderQueue(__("Completed Today"), completed) +
		"</div>";
	page.main.html(html);

	page.main.off("click");

	page.main.on("click", ".doctor-queue-row", function () {
		frappe.set_route("Form", "Patient Encounter", $(this).data("name"));
	});

	page.main.on("click", ".history-badge.clickable", function (event) {
		event.stopPropagation();
		const target = $(this).siblings(".history-list");
		const indicator = $(this).find(".history-expand-indicator");
		if (target.length) {
			target.toggle();
			indicator.toggleClass("expanded");
		}
	});

	page.main.on("click", ".history-list a", function (event) {
		event.stopPropagation();
		frappe.set_route("Form", "Patient Encounter", $(this).data("name"));
	});

	page.main.on("click", ".doctor-action-btn", function (event) {
		event.stopPropagation();
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
		'<div class="welcome"><h3>' +
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
		const response = await frappe.call({
			method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_patient_registration_details",
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
				: '<span class="pending">' + __("pending") + "</span>";
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

	const diagnosis = (row.diagnosis || [])
		.map(
			(entry) =>
				"<li>" +
				frappe.utils.escape_html(entry.diagnosis_name) +
				(entry.notes ? " -- " + frappe.utils.escape_html(entry.notes) : "") +
				"</li>"
		)
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
			: "") +
		(diagnosis
			? '<h5 class="detail-heading">' + __("Diagnosis") + "</h5><ul>" + diagnosis + "</ul>"
			: "")
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
					{
						fieldtype: "Int",
						fieldname: "duration_days",
						label: __("Days"),
						in_list_view: 1,
					},
					{ fieldtype: "Int", fieldname: "quantity", label: __("Qty"), in_list_view: 1 },
					{
						fieldtype: "Small Text",
						fieldname: "instructions",
						label: __("Instructions"),
					},
				],
				data: [],
			},
		],
		primary_action_label: __("Prescribe"),
		primary_action: async (values) => {
			const rows = (values.prescriptions || []).filter((row) => row.medicines);
			if (!rows.length) {
				frappe.msgprint(__("Add at least one medicine."));
				return;
			}
			dialog.hide();
			await submitDoctorAction(page, "prescribe_medicine", {
				encounter,
				prescriptions: rows,
			});
		},
	});
	dialog.show();
}

function openCompleteDialog(page, encounter) {
	const dialog = new frappe.ui.Dialog({
		title: __("Mark Complete"),
		fields: [
			{ fieldtype: "Data", fieldname: "diagnosis", label: __("Diagnosis (optional)") },
			{
				fieldtype: "Small Text",
				fieldname: "clinical_notes",
				label: __("Clinical Notes (optional)"),
			},
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
		await frappe.call({
			method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form." + method,
			args,
		});
	} finally {
		frappe.dom.unfreeze();
	}

	frappe.show_alert({ message: __("Saved"), indicator: "green" });
	await loadQueues(page);
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

function renderActionButtons(encounter) {
	const buttons = [actionButton(encounter.name, "details", __("Details"))];

	if (encounter.custom_workflow_state === "Waiting for Doctor") {
		buttons.push(actionButton(encounter.name, "order_test", __("Order Test")));
		buttons.push(actionButton(encounter.name, "prescribe", __("Prescribe Medicine")));
		buttons.push(actionButton(encounter.name, "complete", __("Mark Complete")));
	} else if (encounter.custom_workflow_state === "Awaiting Doctor Review") {
		buttons.push(actionButton(encounter.name, "prescribe", __("Prescribe Medicine")));
		buttons.push(actionButton(encounter.name, "complete", __("Mark Complete")));
	}

	return '<div class="doctor-action-btns">' + buttons.join("") + "</div>";
}

function renderClinicalSummary(encounter) {
	const parts = [];
	const tests = encounter.tests || [];
	const prescriptions = encounter.prescriptions || [];

	if (tests.length) {
		const done = tests.filter((test) => test.result_type).length;
		parts.push(
			done === tests.length
				? tests.length + " " + __("test(s) done")
				: done + "/" + tests.length + " " + __("test(s) done")
		);
	}
	if (prescriptions.length) {
		const dispensed = prescriptions.filter((prescription) => prescription.dispensed).length;
		parts.push(
			dispensed === prescriptions.length
				? prescriptions.length + " " + __("medicine(s) dispensed")
				: prescriptions.length + " " + __("medicine(s) prescribed")
		);
	}
	if (!parts.length) return '<span class="pending">' + __("Nothing recorded yet") + "</span>";
	return parts.map(frappe.utils.escape_html).join("<br>");
}

function renderQueue(title, encounters) {
	const count = '<span class="queue-meta"> (' + encounters.length + ")</span>";

	if (!encounters.length) {
		return (
			'<div class="queue-section">' +
			'<h4 class="queue-head">' +
			frappe.utils.escape_html(title) +
			count +
			"</h4>" +
			'<div class="empty-state">' +
			'<i class="fa fa-inbox empty-state-icon small"></i>' +
			'<span class="empty-state-text">' +
			__("No patients.") +
			"</span>" +
			"</div></div>"
		);
	}

	const rows = encounters
		.map((encounter) => {
			const visitCount = encounter.history.length;
			const isFirstVisit = visitCount <= 1;
			const badgeClass = isFirstVisit ? "first-visit" : "repeat clickable";
			const badgeLabel = isFirstVisit
				? __("First Visit")
				: __("Repeat Patient") + " &bull; " + visitCount + " " + __("Visits");
			const expandIndicator = isFirstVisit
				? ""
				: '<span class="history-expand-indicator"><i class="fa fa-chevron-down"></i></span>';

			let historyList = "";
			if (!isFirstVisit) {
				const items = encounter.history
					.map((visit) => {
						const visitDate = frappe.datetime.str_to_user(visit.encounter_date);
						return (
							"<li><a data-name='" +
							frappe.utils.escape_html(visit.name) +
							"'>" +
							frappe.utils.escape_html(visitDate) +
							"</a></li>"
						);
					})
					.join("");
				historyList = '<ul class="history-list">' + items + "</ul>";
			}

			return (
				'<tr class="doctor-queue-row" data-name="' +
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
				'<td class="history-cell">' +
				'<span class="history-badge ' +
				badgeClass +
				'" data-patient="' +
				frappe.utils.escape_html(encounter.patient) +
				'">' +
				badgeLabel +
				expandIndicator +
				"</span>" +
				historyList +
				"</td>" +
				'<td class="clinical-cell">' +
				renderClinicalSummary(encounter) +
				"</td>" +
				"<td>" +
				renderActionButtons(encounter) +
				"</td>" +
				"</tr>"
			);
		})
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
