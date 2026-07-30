frappe.ui.form.on("Patient", {
	custom_height_m: function (frm) {
		if (frm.doc.custom_height_m && frm.doc.custom_weight_kg) {
			calculate_bmi(frm);
		}
	},

	custom_weight_kg: function (frm) {
		if (frm.doc.custom_height_m && frm.doc.custom_weight_kg) {
			calculate_bmi(frm);
		}
	},
});

let calculate_bmi = function (frm) {
	var h = flt(frm.doc.custom_height_m);
	var w = flt(frm.doc.custom_weight_kg);
	if (h <= 0 || w <= 0) return;
	var bmi = (w / (h * h)).toFixed(2);
	frm.set_value("custom_bmi", bmi);
};
