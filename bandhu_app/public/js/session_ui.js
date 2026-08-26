/* global bandhu */

// Shared session/queue UI for the CAD, Doctor, Nurse and My Schedule desk pages.
//
// Desk page scripts run inside `new Function(...)` (frappe/public/js/frappe/dom.js:30), so they
// cannot see each other's helpers. Each page pulls this file in with `frappe.require` before it
// renders; frappe.assets caches it, so only the first page of a session pays for the fetch.

frappe.provide("bandhu.session_ui");

(function () {
	// frappe.call REJECTS on network failure (frappe/public/js/frappe/request.js:32-41). Without
	// this wrapper the rejection escapes unhandled and page.main is never written, leaving staff
	// on a weak camp signal staring at a blank screen with no message and no way to retry.
	async function refresh_page(page, load) {
		try {
			await load(page);
		} catch (error) {
			page.main.html(format_load_error());
			page.main.off("click", ".load-error-retry");
			page.main.on("click", ".load-error-retry", () => refresh_page(page, load));
		}
	}

	function format_load_error() {
		return (
			'<div class="bandhu-load-error">' +
			'<i class="fa fa-exclamation-triangle load-error-icon"></i>' +
			'<span class="load-error-text">' +
			__("Could not load this page. Check the network connection and try again.") +
			"</span>" +
			'<button type="button" class="btn btn-primary load-error-retry">' +
			__("Retry") +
			"</button></div>"
		);
	}

	function format_welcome() {
		return (
			'<div class="welcome"><h3>' +
			__("Welcome, {0}", [frappe.utils.escape_html(frappe.user_info().fullname)]) +
			"</h3></div>"
		);
	}

	function format_session_info(session) {
		const running_class = session.status === "In Progress" ? " running" : "";
		return (
			'<div class="session-bar">' +
			'<i class="fa fa-hospital-o"></i> ' +
			frappe.utils.escape_html(session.clinic || "") +
			'<span class="session-sep">|</span>' +
			'<i class="fa fa-map-marker"></i> ' +
			frappe.utils.escape_html(session.site || "") +
			'<span class="session-sep">|</span>' +
			'<i class="fa fa-circle session-dot' +
			running_class +
			'"></i> ' +
			frappe.utils.escape_html(session.status) +
			"</div>"
		);
	}

	// A Time field arrives as "9:30:00", not "09:30:00", so it cannot simply be truncated.
	function format_clock_time(value) {
		if (!value) return "";
		const [hours, minutes] = String(value).split(":");
		const hour = parseInt(hours, 10);
		const suffix = hour < 12 ? __("AM") : __("PM");
		const hour_12 = hour % 12 === 0 ? 12 : hour % 12;
		return hour_12 + ":" + (minutes || "00").padStart(2, "0") + " " + suffix;
	}

	function format_planned_window(session) {
		if (!session.planned_start_time) return "";
		const start = format_clock_time(session.planned_start_time);
		return session.planned_end_time
			? start + " – " + format_clock_time(session.planned_end_time)
			: start;
	}

	async function get_upcoming_sessions(method) {
		try {
			const response = await frappe.call({ method });
			return (response && response.message) || [];
		} catch (error) {
			// The upcoming list is informational; failing to load it must not blank the page.
			return [];
		}
	}

	function format_upcoming_sessions(sessions) {
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
					frappe.utils.escape_html(format_planned_window(session)) +
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

	// Desk's own read-only field shape — a small muted label above its value, laid out in the
	// grid and typography classes the desk bundle already ships. Nothing here is page CSS of
	// ours, so the dialog keeps following Desk across a Frappe upgrade instead of drifting.
	function format_detail_field(label, value) {
		if (value === null || value === undefined || value === "") return "";
		return (
			'<div class="col-6 col-md-4 mb-4">' +
			'<div class="control-label text-xs">' +
			frappe.utils.escape_html(label) +
			"</div>" +
			'<div class="text-sm text-ink-gray-8">' +
			frappe.utils.escape_html(String(value)) +
			"</div></div>"
		);
	}

	function format_vitals(patient) {
		return [
			patient.custom_height_m ? patient.custom_height_m + " m" : null,
			patient.custom_weight_kg ? patient.custom_weight_kg + " kg" : null,
			patient.custom_bmi ? __("BMI") + " " + patient.custom_bmi : null,
		]
			.filter(Boolean)
			.join(" · ");
	}

	function format_registration_details(patient) {
		const fields =
			format_detail_field(__("Clinic ID"), patient.custom_bandhu_id) +
			format_detail_field(__("ABHA ID"), patient.custom_abha_id) +
			format_detail_field(__("Mobile"), patient.mobile) +
			// The endpoint returns the stored date; every other Bandhu screen shows dates in
			// the user's own format, so printing it raw here is the odd one out.
			format_detail_field(
				__("Date of Birth"),
				patient.dob ? frappe.datetime.str_to_user(patient.dob) : ""
			) +
			format_detail_field(__("Vitals"), format_vitals(patient)) +
			format_detail_field(__("Temperature"), patient.custom_temperature) +
			format_detail_field(__("Native State"), patient.custom_native_state) +
			format_detail_field(__("Native District"), patient.custom_native_district) +
			format_detail_field(
				__("Sector of Employment"),
				patient.custom_sector_of_employment
			) +
			format_detail_field(__("Company"), patient.custom_name_of_company);

		return fields ? '<div class="row">' + fields + "</div>" : "";
	}

	function format_badge(label, theme, variant) {
		return (
			'<span class="es-badge" data-theme="' +
			theme +
			'" data-variant="' +
			variant +
			'">' +
			frappe.utils.escape_html(label) +
			"</span>"
		);
	}

	// Positive is the one result a nurse must not walk past, so it is the only solid badge.
	const TEST_RESULT_BADGES = {
		Positive: { theme: "red", variant: "solid" },
		Negative: { theme: "green", variant: "subtle" },
	};

	// The Bandhu Test master decides whether a result reads as a measurement or an indicator;
	// the row cannot, because an ordered-but-untested row carries no result_type at all.
	function format_test_result(test) {
		if (test.result_shape === "Value" || test.result_type === "Value") {
			return test.result_value
				? format_badge(format_measurement(test), "blue", "subtle")
				: format_badge(__("Pending"), "amber", "subtle");
		}

		const badge = TEST_RESULT_BADGES[test.result_type];
		return badge
			? format_badge(test.result_type, badge.theme, badge.variant)
			: format_badge(__("Pending"), "amber", "subtle");
	}

	// Results entered before the master carried a unit already have it typed into the value.
	function format_measurement(test) {
		const reading = String(test.result_value);
		return test.unit && !reading.includes(test.unit) ? reading + " " + test.unit : reading;
	}

	function format_note(note) {
		return (
			'<div class="text-xs text-muted mt-1">' +
			__("Note") +
			": " +
			frappe.utils.escape_html(note) +
			"</div>"
		);
	}

	function format_row_open() {
		return '<div class="flex items-baseline justify-between gap-3 py-1.5">';
	}

	// `shared_note` is the doctor's one ordering note when it covers every row (see
	// utils/patient_details.shared_test_note); those rows drop it so it prints once, above.
	function format_test_rows(tests, shared_note) {
		return (tests || [])
			.map((test) => {
				const own_note = (test.notes || "").trim();
				return (
					format_row_open() +
					'<div class="min-w-0"><div class="text-sm text-ink-gray-8">' +
					frappe.utils.escape_html(test.test_name) +
					"</div>" +
					(own_note && own_note !== shared_note ? format_note(own_note) : "") +
					'</div><div class="shrink-0">' +
					format_test_result(test) +
					"</div></div>"
				);
			})
			.join("");
	}

	function format_prescription_rows(prescriptions) {
		return (prescriptions || [])
			.map((prescription) => {
				const schedule = [
					prescription.dosage_frequency,
					prescription.duration_days ? prescription.duration_days + "d" : null,
					prescription.quantity ? "x" + prescription.quantity : null,
				]
					.filter(Boolean)
					.join(" ");
				return (
					format_row_open() +
					'<div class="min-w-0"><div class="text-sm text-ink-gray-8">' +
					frappe.utils.escape_html(prescription.medicines) +
					(schedule
						? '<span class="text-xs text-muted ms-2">' +
						  frappe.utils.escape_html(schedule) +
						  "</span>"
						: "") +
					"</div>" +
					(prescription.instructions ? format_note(prescription.instructions) : "") +
					'</div><div class="shrink-0">' +
					(prescription.dispensed
						? format_badge(__("Dispensed"), "green", "subtle")
						: format_badge(__("Pending"), "amber", "subtle")) +
					"</div></div>"
				);
			})
			.join("");
	}

	function format_diagnosis_rows(diagnosis) {
		return (diagnosis || [])
			.map(
				(entry) =>
					'<div class="py-1.5"><div class="text-sm text-ink-gray-8">' +
					frappe.utils.escape_html(entry.diagnosis_name) +
					"</div>" +
					(entry.notes ? format_note(entry.notes) : "") +
					"</div>"
			)
			.join("");
	}

	function format_section(title, body, lead) {
		if (!body) return "";
		return (
			'<div class="mt-4"><div class="text-base-semibold text-ink-gray-8 mb-2">' +
			frappe.utils.escape_html(title) +
			"</div>" +
			(lead ? '<div class="text-sm text-muted mb-2">' + lead + "</div>" : "") +
			body +
			"</div>"
		);
	}

	// The nurse queue rows carry no diagnosis, so that section simply renders empty for them.
	function format_patient_details(patient, encounter) {
		const shared_note = (encounter.shared_test_note || "").trim();
		return (
			format_section(__("Registration Details"), format_registration_details(patient)) +
			format_section(
				__("Tests"),
				format_test_rows(encounter.tests, shared_note),
				shared_note ? __("Note") + ": " + frappe.utils.escape_html(shared_note) : ""
			) +
			format_section(
				__("Prescriptions"),
				format_prescription_rows(encounter.prescriptions)
			) +
			format_section(__("Diagnosis"), format_diagnosis_rows(encounter.diagnosis))
		);
	}

	async function open_patient_details_dialog(method, encounter_name, encounter) {
		frappe.dom.freeze();
		let patient;
		try {
			const response = await frappe.call({ method, args: { encounter: encounter_name } });
			patient = response.message || {};
		} finally {
			frappe.dom.unfreeze();
		}

		const dialog = new frappe.ui.Dialog({
			title: __("Patient Details"),
			size: "large",
			fields: [{ fieldtype: "HTML", fieldname: "details_html" }],
		});
		dialog.fields_dict.details_html.$wrapper.html(format_patient_details(patient, encounter));
		dialog.show();
	}

	function format_action_button(button_class, encounter_name, action, label, is_primary) {
		return (
			'<button type="button" class="btn btn-sm ' +
			(is_primary ? "btn-primary" : "btn-default") +
			" queue-action-btn " +
			button_class +
			'" data-encounter="' +
			frappe.utils.escape_html(encounter_name) +
			'" data-action="' +
			frappe.utils.escape_html(action) +
			'">' +
			frappe.utils.escape_html(label) +
			"</button>"
		);
	}

	Object.assign(bandhu.session_ui, {
		refresh_page,
		format_load_error,
		format_welcome,
		format_session_info,
		format_clock_time,
		format_planned_window,
		get_upcoming_sessions,
		format_upcoming_sessions,
		format_patient_details,
		open_patient_details_dialog,
		format_action_button,
	});
})();
