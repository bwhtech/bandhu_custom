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

	function format_detail_row(label, value) {
		if (value === null || value === undefined || value === "") return "";
		return (
			'<div class="detail-row"><span>' +
			frappe.utils.escape_html(label) +
			"</span><span>" +
			frappe.utils.escape_html(String(value)) +
			"</span></div>"
		);
	}

	function format_registration_details(patient) {
		return (
			format_detail_row(__("Clinic ID"), patient.custom_bandhu_id) +
			format_detail_row(__("ABHA ID"), patient.custom_abha_id) +
			format_detail_row(__("Mobile"), patient.mobile) +
			format_detail_row(__("Date of Birth"), patient.dob) +
			format_detail_row(__("Height (m)"), patient.custom_height_m) +
			format_detail_row(__("Weight (kg)"), patient.custom_weight_kg) +
			format_detail_row(__("BMI"), patient.custom_bmi) +
			format_detail_row(__("Temperature"), patient.custom_temperature) +
			format_detail_row(__("Native State"), patient.custom_native_state) +
			format_detail_row(__("Native District"), patient.custom_native_district) +
			format_detail_row(__("Sector of Employment"), patient.custom_sector_of_employment) +
			format_detail_row(__("Company"), patient.custom_name_of_company)
		);
	}

	function format_test_items(tests) {
		return (tests || [])
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
	}

	function format_prescription_items(prescriptions) {
		return (prescriptions || [])
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
	}

	function format_diagnosis_items(diagnosis) {
		return (diagnosis || [])
			.map(
				(entry) =>
					"<li>" +
					frappe.utils.escape_html(entry.diagnosis_name) +
					(entry.notes ? " -- " + frappe.utils.escape_html(entry.notes) : "") +
					"</li>"
			)
			.join("");
	}

	function format_section(title, items) {
		if (!items) return "";
		return '<h5 class="detail-heading">' + title + "</h5><ul>" + items + "</ul>";
	}

	// The nurse queue rows carry no diagnosis, so that section simply renders empty for them.
	function format_patient_details(patient, encounter) {
		return (
			"<h5>" +
			__("Registration Details") +
			"</h5>" +
			format_registration_details(patient) +
			format_section(__("Tests"), format_test_items(encounter.tests)) +
			format_section(
				__("Prescriptions"),
				format_prescription_items(encounter.prescriptions)
			) +
			format_section(__("Diagnosis"), format_diagnosis_items(encounter.diagnosis))
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
		format_detail_row,
		format_patient_details,
		open_patient_details_dialog,
		format_action_button,
	});
})();
