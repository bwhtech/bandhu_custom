var _nurse_css =
	".nurse-dash{--max-w:var(--page-max-width,900px);max-width:var(--max-w);margin:0 auto;padding:0 var(--padding-md);}" +
	".nurse-dash .empty-state{display:flex;flex-direction:column;align-items:center;padding:var(--padding-2xl) var(--padding-md);border:1px solid var(--border-color);border-radius:var(--border-radius-md);color:var(--text-muted);background:var(--bg-color);}" +
	".nurse-dash .table-wrap{overflow:auto;border:1px solid var(--table-border-color);border-radius:var(--border-radius-md);margin-top:var(--margin-sm);max-height:360px;}" +
	".nurse-dash .table{margin-bottom:0;min-width:400px;}" +
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
	"@media(max-width:768px){" +
	".nurse-dash{padding:0 var(--padding-sm);}" +
	".nurse-dash .table{min-width:350px;}" +
	".nurse-dash .table td,.nurse-dash .table th{padding:8px 10px;}}";

var _nurse_session = null;

frappe.pages["nurse-form"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Nurse Dashboard"),
		single_column: true,
	});

	page.set_secondary_action(__("Refresh"), function () {
		load_dashboard(page);
	});

	load_dashboard(page);
};

function load_dashboard(page) {
	frappe.dom.freeze();
	frappe.call({
		method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_session_status",
		callback: function (r) {
			frappe.dom.unfreeze();
			var data = r.message || {};

			if (!data.has_session) {
				page.main.html(
					"<style>" +
						_nurse_css +
						"</style>" +
						'<div class="nurse-dash">' +
						render_welcome() +
						'<div class="empty-state">' +
						'<i class="fa fa-calendar-o" style="font-size:32px;margin-bottom:10px;opacity:0.4;"></i>' +
						'<span style="font-size:var(--text-sm);">' +
						frappe.utils.escape_html(data.message) +
						"</span></div></div>"
				);
				return;
			}

			_nurse_session = data;

			if (data.status === "Planned") {
				page.main.html(
					"<style>" +
						_nurse_css +
						"</style>" +
						'<div class="nurse-dash">' +
						render_welcome() +
						render_session_info(data) +
						'<div style="padding:var(--padding-xl) 0;display:flex;justify-content:center;">' +
						'<button class="btn btn-primary btn-lg nurse-start-session">' +
						'<i class="fa fa-play"></i> ' +
						__("Start Session") +
						"</button></div></div>"
				);

				page.main.on("click", ".nurse-start-session", function () {
					start_session(page);
				});
			} else if (data.status === "In Progress") {
				load_queues(page);
			} else if (data.status === "Completed") {
				page.main.html(
					"<style>" +
						_nurse_css +
						"</style>" +
						'<div class="nurse-dash">' +
						render_welcome() +
						render_session_info(data) +
						'<div class="empty-state">' +
						'<i class="fa fa-check-circle" style="font-size:32px;color:var(--green-500);margin-bottom:10px;"></i>' +
						'<span style="font-size:var(--text-sm);">' +
						__("Session completed. Great work!") +
						"</span></div></div>"
				);
			}
		},
	});
}

function start_session(page) {
	frappe.dom.freeze();
	frappe.call({
		method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.start_session",
		args: { session_name: _nurse_session.session_name },
		callback: function (r) {
			frappe.dom.unfreeze();
			if (r.message && r.message.success) {
				frappe.show_alert({ message: __("Session started"), indicator: "green" });
				load_dashboard(page);
			}
		},
		error: function () {
			frappe.dom.unfreeze();
			frappe.show_alert({ message: __("Failed to start session"), indicator: "red" });
		},
	});
}

function end_session(page) {
	frappe.confirm(__("End the current session?"), function () {
		frappe.dom.freeze();
		frappe.call({
			method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.end_session",
			args: { session_name: _nurse_session.session_name },
			callback: function (r) {
				frappe.dom.unfreeze();
				if (r.message && r.message.success) {
					frappe.show_alert({ message: __("Session ended"), indicator: "green" });
					load_dashboard(page);
				}
			},
			error: function () {
				frappe.dom.unfreeze();
				frappe.show_alert({ message: __("Failed to end session"), indicator: "red" });
			},
		});
	});
}

function load_queues(page) {
	frappe.dom.freeze();
	var session_name = _nurse_session.session_name;
	var done = 0;
	var data = {};

	function check_done() {
		done++;
		if (done < 3) return;
		frappe.dom.unfreeze();
		page.main.html(
			"<style>" +
				_nurse_css +
				"</style>" +
				'<div class="nurse-dash">' +
				render_welcome() +
				render_session_info(_nurse_session) +
				render_end_session_button() +
				render_queue_section(__("Patients for Tests"), data.tests || []) +
				render_queue_section(__("Patients for Medicines"), data.medicines || []) +
				render_queue_section(__("Completed Patients"), data.completed || []) +
				"</div>"
		);

		page.main.on("click", ".nurse-end-session", function () {
			end_session(page);
		});

		page.main.on("click", ".nurse-queue-row", function () {
			var name = $(this).data("name");
			frappe.set_route("Form", "Patient Encounter", name);
		});
	}

	frappe.call({
		method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_patients_for_tests",
		args: { session_name: session_name },
		callback: function (r) {
			data.tests = r.message || [];
			check_done();
		},
	});

	frappe.call({
		method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_patients_for_medicines",
		args: { session_name: session_name },
		callback: function (r) {
			data.medicines = r.message || [];
			check_done();
		},
	});

	frappe.call({
		method: "bandhu_app.bandhu_app.page.nurse_form.nurse_form.get_completed_patients",
		args: { session_name: session_name },
		callback: function (r) {
			data.completed = r.message || [];
			check_done();
		},
	});
}

function render_welcome() {
	var name =
		typeof frappe.user.full_name === "function"
			? frappe.user.full_name()
			: frappe.user.full_name || "Nurse";
	return (
		'<div style="padding:var(--padding-lg) 0 var(--padding-xl) 0;">' +
		"<h3 style='font-size:var(--text-2xl);font-weight:var(--weight-semibold);color:var(--heading-color);margin:0;'>" +
		__("Welcome, {0}", [name]) +
		"</h3></div>"
	);
}

function render_session_info(session) {
	var status_color = session.status === "In Progress" ? "var(--green-500)" : "var(--text-muted)";
	return (
		'<div class="session-bar">' +
		'<i class="fa fa-hospital-o"></i> ' +
		frappe.utils.escape_html(session.clinic || "") +
		'<span style="color:var(--border-color);">|</span>' +
		'<i class="fa fa-map-marker"></i> ' +
		frappe.utils.escape_html(session.site || "") +
		'<span style="color:var(--border-color);">|</span>' +
		'<i class="fa fa-circle" style="color:' +
		status_color +
		';font-size:8px;"></i> ' +
		frappe.utils.escape_html(session.status) +
		"</div>"
	);
}

function render_end_session_button() {
	return (
		'<div style="padding:0 0 var(--padding-lg) 0;">' +
		'<button class="btn btn-danger btn-sm nurse-end-session">' +
		'<i class="fa fa-stop"></i> ' +
		__("End Session") +
		"</button></div>"
	);
}

function render_queue_section(title, patients) {
	var count = '<span class="queue-meta"> (' + patients.length + ")</span>";

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

	var rows = patients
		.map(function (p) {
			return (
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
		"</tr></thead>" +
		"<tbody>" +
		rows +
		"</tbody>" +
		"</table></div></div>"
	);
}
