frappe.pages["doctor-form"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Doctor"),
		single_column: true,
	});

	page.set_secondary_action(__("Refresh"), function () {
		load_queues(page);
	});

	load_queues(page);
};

function load_queues(page) {
	frappe.dom.freeze();
	var data = {};
	var history = {};
	var done = 0;
	var total_calls = 2;

	function check_done() {
		done++;
		if (done < total_calls) return;
		fetch_all_history();
	}

	function fetch_all_history() {
		var patients = new Set();
		(data.active || []).concat(data.completed || []).forEach(function (p) {
			if (p.patient) patients.add(p.patient);
		});
		patients = Array.from(patients);
		if (!patients.length) {
			render(page, data, history);
			return;
		}
		var history_done = 0;
		patients.forEach(function (patient) {
			frappe.call({
				method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_patient_history",
				args: { patient: patient },
				callback: function (r) {
					history[patient] = r.message || [];
					history_done++;
					if (history_done === patients.length) {
						render(page, data, history);
					}
				},
			});
		});
	}

	function render(page, data, history) {
		frappe.dom.unfreeze();
		var active = (data.active || []).map(function (p) {
			p._history = history[p.patient] || [];
			return p;
		});
		var completed = (data.completed || []).map(function (p) {
			p._history = history[p.patient] || [];
			return p;
		});

		var html =
			"<style>" +
			".doctor-dash{--max-w:var(--page-max-width,900px);max-width:var(--max-w);margin:0 auto;padding:0 var(--padding-md);}" +
			".doctor-dash .empty-state{display:flex;flex-direction:column;align-items:center;padding:var(--padding-2xl) var(--padding-md);border:1px solid var(--border-color);border-radius:var(--border-radius-md);color:var(--text-muted);background:var(--bg-color);}" +
			".doctor-dash .table-wrap{overflow:auto;border:1px solid var(--table-border-color);border-radius:var(--border-radius-md);margin-top:var(--margin-sm);max-height:360px;}" +
			".doctor-dash .table{margin-bottom:0;min-width:480px;}" +
			".doctor-dash .table thead{position:sticky;top:0;z-index:1;}" +
			".doctor-dash .table th{background:var(--subtle-fg);padding:8px 12px;font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--heading-color);white-space:nowrap;border-bottom:1px solid var(--table-border-color);}" +
			".doctor-dash .table td{padding:10px 12px;vertical-align:middle;border-bottom:1px solid var(--table-border-color);}" +
			".doctor-dash .table tbody tr:last-child td{border-bottom:none;}" +
			".doctor-queue-row{cursor:pointer;}" +
			".doctor-dash .queue-head{font-size:var(--text-lg);font-weight:var(--weight-semibold);color:var(--heading-color);margin:0;}" +
			".doctor-dash .queue-meta{font-weight:var(--weight-regular);font-size:var(--text-base);color:var(--text-muted);}" +
			".doctor-dash .queue-section{margin-bottom:var(--margin-2xl);}" +
			".doctor-dash .queue-section:last-child{margin-bottom:0;}" +
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
			"@media(max-width:768px){" +
			".doctor-dash{padding:0 var(--padding-sm);}" +
			".doctor-dash .table{min-width:400px;}" +
			".doctor-dash .table td,.doctor-dash .table th{padding:8px 10px;}" +
			"}</style>" +
			'<div class="doctor-dash">' +
			render_welcome() +
			render_queue(__("Active Patients"), active) +
			render_queue(__("Completed Today"), completed) +
			"</div>";
		page.main.html(html);

		page.main.on("click", ".doctor-queue-row", function () {
			var name = $(this).data("name");
			frappe.set_route("Form", "Patient Encounter", name);
		});

		page.main.on("click", ".history-badge.clickable", function (e) {
			e.stopPropagation();
			var patient = $(this).data("patient");
			var target = $(this).siblings(".history-list");
			var indicator = $(this).find(".history-expand-indicator");
			if (target.length) {
				target.toggle();
				indicator.toggleClass("expanded");
			}
		});

		page.main.on("click", ".history-list a", function (e) {
			e.stopPropagation();
			var name = $(this).data("name");
			frappe.set_route("Form", "Patient Encounter", name);
		});
	}

	frappe.call({
		method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_registered_patients",
		callback: function (r) {
			data.active = r.message || [];
			check_done();
		},
	});

	frappe.call({
		method: "bandhu_app.bandhu_app.page.doctor_form.doctor_form.get_completed_patients",
		callback: function (r) {
			data.completed = r.message || [];
			check_done();
		},
	});
}

function render_welcome() {
	var name =
		(typeof frappe.user.full_name === "function"
			? frappe.user.full_name()
			: frappe.user.full_name) || "Doctor";
	return (
		'<div style="padding:var(--padding-lg) 0 var(--padding-xl) 0;">' +
		"<h3 style='font-size:var(--text-2xl);font-weight:var(--weight-semibold);color:var(--heading-color);margin:0;'>" +
		__("Welcome, {0}", [name]) +
		"</h3></div>"
	);
}

function render_queue(title, patients) {
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
			__("No patients.") +
			"</span>" +
			"</div></div>"
		);
	}

	var rows = patients
		.map(function (p) {
			var total = p._history.length;
			var is_first = total <= 1;
			var badge_class = is_first ? "first-visit" : "repeat clickable";
			var badge_label = is_first
				? __("First Visit")
				: __("Repeat Patient") + " &bull; " + total + " " + __("Visits");
			var expand_indicator = is_first
				? ""
				: '<span class="history-expand-indicator"><i class="fa fa-chevron-down"></i></span>';

			var history_list = "";
			if (!is_first) {
				var items = p._history
					.map(function (h) {
						var d = frappe.datetime.str_to_user(h.encounter_date);
						return (
							"<li><a data-name='" +
							frappe.utils.escape_html(h.name) +
							"'>" +
							frappe.utils.escape_html(d) +
							"</a></li>"
						);
					})
					.join("");
				history_list = '<ul class="history-list" style="display:none;">' + items + "</ul>";
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
				badge_class +
				'" data-patient="' +
				frappe.utils.escape_html(p.patient) +
				'">' +
				badge_label +
				expand_indicator +
				"</span>" +
				history_list +
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
		"</tr></thead>" +
		"<tbody>" +
		rows +
		"</tbody>" +
		"</table></div></div>"
	);
}
