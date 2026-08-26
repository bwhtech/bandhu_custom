/* global bandhu */

const SESSION_UI_ASSET = "/assets/bandhu_app/js/session_ui.js";

let encountersByName = {};
let testOptions = null;
let doctorSession = null;
let doctorPage = null;

// One call for the whole queue. Fetching per patient meant a 40-patient camp fired 40 parallel
// requests, saturating the browser connection pool on a weak link.
async function getPatientHistories(patients) {
	if (!patients.length) return {};
	const response = await frappe.call({
		method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_patient_histories",
		args: { patients },
	});
	return response.message || {};
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
		const upcoming = await bandhu.session_ui.get_upcoming_sessions(
			"bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_upcoming_sessions"
		);
		renderNoSession(page, status.message, upcoming);
		return;
	}

	doctorSession = status;
	await loadQueues(page);
}

function renderNoSession(page, message, upcoming) {
	page.main.html(
		'<div class="doctor-dash">' +
			bandhu.session_ui.format_welcome() +
			'<div class="empty-state">' +
			frappe.utils.icon("calendar-off", "xl", "", "", "current-color empty-state-icon") +
			'<span class="empty-state-text">' +
			frappe.utils.escape_html(message || __("No session available.")) +
			"</span></div>" +
			bandhu.session_ui.format_upcoming_sessions(upcoming) +
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
		const historyByPatient = await getPatientHistories(patients);

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
		bandhu.session_ui.format_welcome() +
		(doctorSession ? bandhu.session_ui.format_session_info(doctorSession) : "") +
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

async function dispatchDoctorAction(page, encounter, action) {
	switch (action) {
		case "details":
			bandhu.session_ui.open_patient_details_dialog(
				"bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_patient_registration_details",
				encounter,
				encountersByName[encounter] || {}
			);
			break;
		case "order_test":
			await openOrderTestDialog(page, encounter);
			break;
		case "prescribe":
			openPrescribeDialog(page, encounter);
			break;
		case "complete":
			openCompleteDialog(page, encounter);
			break;
	}
}

// The clinic's test list is a master, so the checkboxes cannot be a constant. Fetched once
// per page load rather than per dialog — it changes when an admin edits the master, not
// between two patients.
async function getTestOptions() {
	if (!testOptions) {
		const response = await frappe.call({
			method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_test_options",
		});
		testOptions = (response.message || []).map((test) => ({
			label: test.label,
			value: test.name,
		}));
	}
	return testOptions;
}

async function openOrderTestDialog(page, encounter) {
	const options = await getTestOptions();
	if (!options.length) {
		frappe.msgprint(__("No tests are configured. Ask an administrator to add one."));
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Order Tests"),
		fields: [
			{
				fieldtype: "MultiCheck",
				fieldname: "tests",
				label: __("Tests"),
				options,
				// The master's display_order is the clinic's chosen order; MultiCheck
				// re-sorts alphabetically unless told not to.
				sort_options: false,
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
	await bandhu.session_ui.refresh_page(page, loadQueues);
}

function renderActionButtons(encounter) {
	const actions = [["details", __("Details")]];

	if (encounter.custom_workflow_state === "Waiting for Doctor") {
		actions.push(["order_test", __("Order Test")]);
	}
	if (
		encounter.custom_workflow_state === "Waiting for Doctor" ||
		encounter.custom_workflow_state === "Awaiting Doctor Review"
	) {
		actions.push(["prescribe", __("Prescribe Medicine")]);
		actions.push(["complete", __("Mark Complete")]);
	}

	const buttons = actions
		.map(([action, label]) =>
			bandhu.session_ui.format_action_button(
				"doctor-action-btn",
				encounter.name,
				action,
				label,
				false
			)
		)
		.join("");

	return '<div class="doctor-action-btns">' + buttons + "</div>";
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
			frappe.utils.icon("inbox", "xl", "", "", "current-color empty-state-icon small") +
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
				: '<span class="history-expand-indicator">' +
				  frappe.utils.icon("chevron-down", "xs", "", "", "current-color") +
				  "</span>";

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
				'<td class="patient-cell">' +
				frappe.utils.escape_html(encounter.patient_name || "") +
				"</td>" +
				'<td class="age-cell">' +
				frappe.utils.escape_html(encounter.patient_age || "") +
				"</td>" +
				'<td class="sex-cell">' +
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
				'<td class="action-cell">' +
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

	page.set_secondary_action(__("Refresh"), refreshDashboard);
	page.set_primary_action(__("My Schedule"), () => frappe.set_route("my-schedule"), "calendar");

	doctorPage = page;
};

async function refreshDashboard() {
	await frappe.require(SESSION_UI_ASSET);
	await bandhu.session_ui.refresh_page(doctorPage, loadDashboard);
}

// Desk keeps this page's DOM and module state alive, so returning from a Patient Encounter would
// otherwise show the queue exactly as it was before the encounter was edited -- a doctor could
// prescribe again for a patient they had just completed. on_page_show also fires on the very first
// show (frappe/public/js/frappe/views/pageview.js:104-107), so it is the only loader needed.
frappe.pages["doctor-form"].on_page_show = refreshDashboard;
