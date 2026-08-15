// Copyright (c) 2026, CMID and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Bandhu Clinic Session", {
// 	refresh(frm) {

// 	},
// });

// frappe.ui.form.on('Bandhu Clinic Session', {
// 	refresh(frm) {
// 		// your code here
// 	}
// })

frappe.ui.form.on("Bandhu Clinic Session", {
	refresh: function (frm) {
		// START BUTTON
		if (frm.doc.status === "Planned") {
			frm.add_custom_button(__("Start Session"), async () => {
				// basic guard
				if (!frm.doc.clinic || !frm.doc.date) {
					frappe.msgprint(__("Please set Clinic and Date before starting."));
					return;
				}

				frm.set_value("status", "In Progress");
				frm.set_value("start_time", frappe.datetime.now_datetime());
				await frm.save();

				frappe.show_alert({ message: __("Session Started"), indicator: "green" });
			});
		}

		// END BUTTON
		if (frm.doc.status === "In Progress") {
			frm.add_custom_button(__("End Session"), async () => {
				// optional safety checks
				// (keep light for now)
				frm.set_value("status", "Completed");
				frm.set_value("end_time", frappe.datetime.now_datetime());
				await frm.save();

				frappe.show_alert({ message: __("Session Completed"), indicator: "blue" });
			});
		}

		// A cancelled session stays on record on purpose: the recurring schedule skips any
		// date that already has a session, so the cancellation is what stops tonight's job
		// from putting this one back.
		if (frm.doc.status === "Planned") {
			frm.add_custom_button(__("Cancel Session"), async () => {
				const confirmed = await new Promise((resolve) => {
					frappe.confirm(
						__("Cancel this session? It will not be recreated by the schedule."),
						() => resolve(true),
						() => resolve(false)
					);
				});
				if (!confirmed) return;

				frm.set_value("status", "Cancelled");
				await frm.save();
				frappe.show_alert({ message: __("Session Cancelled"), indicator: "red" });
			});
		}

		if (frm.doc.status === "Cancelled") {
			frm.add_custom_button(__("Reopen Session"), async () => {
				frm.set_value("status", "Planned");
				await frm.save();
				frappe.show_alert({ message: __("Session Reopened"), indicator: "green" });
			});
		}
	},
});
