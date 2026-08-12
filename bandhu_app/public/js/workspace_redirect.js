// Clicking the CAD / Doctor / Nurse workspace icon in the Desk sidebar
// used to land on the generic Workspace shortcut screen (Patient/Vehicle
// list shortcuts), forcing field staff to hunt for the actual working
// page. Bounce straight into the real Desk Page instead.
const WORKSPACE_TO_WORKING_PAGE = {
	cad: "cad-form",
	doctor: "doctor-form",
	nurse: "nurse-form",
};

frappe.router.on("change", () => {
	const route = frappe.get_route();
	if (route[0] !== "Workspaces") {
		return;
	}

	const working_page = WORKSPACE_TO_WORKING_PAGE[frappe.router.slug(route[1] || "")];
	if (working_page) {
		frappe.set_route(working_page);
	}
});
