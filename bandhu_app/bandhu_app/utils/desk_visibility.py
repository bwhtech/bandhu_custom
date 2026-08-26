import frappe

# Other apps ship their own Desktop Icons for the /desk grid with no role restriction, so
# every Desk user sees ERPNext's Accounting/Buying/Stock and friends whether or not they
# mean anything to a nurse. We don't own those apps' fixtures (never edit apps/frappe,
# apps/erpnext — lost on bench update), and each app's own `bench migrate` re-syncs its
# icons from its own JSON on every run, silently wiping a restriction set directly on the
# doc. Running this again after every migrate, via the after_migrate hook, is what makes it
# stick.
#
# Matched by rule rather than by name: an earlier hardcoded list ("Framework", "Quality",
# "Marley Health") missed every ERPNext icon and named one that does not exist on this
# site at all. Restricting the top-level icons is enough — children render under their
# parent, so hiding the parent hides the branch.
ALLOWED_ROLES = ["System Manager"]


def restrict_other_app_desktop_icons():
	"""Hide other apps' top-level desk icons from everyone but System Manager."""
	foreign_icons = frappe.get_all(
		"Desktop Icon",
		filters={"app": ["!=", "bandhu_app"], "parent_icon": ["in", ["", None]]},
		pluck="name",
	)

	for icon_name in foreign_icons:
		icon = frappe.get_doc("Desktop Icon", icon_name)
		if {row.role for row in icon.roles} == set(ALLOWED_ROLES):
			continue

		icon.set("roles", [{"role": role} for role in ALLOWED_ROLES])
		try:
			icon.save()
		except Exception as error:
			# Another app's icon can point at a workspace that no longer exists (erpnext ships
			# "Subcontracting" that way here), and its save fails link validation. That is not
			# ours to repair, and it must not stop the icons after it in the list from being
			# hidden — which is exactly what happened before this was caught.
			frappe.log_error(
				title="Could not restrict desktop icon", message=f"{icon_name}: {error}"
			)


def sync_bandhu_desktop_icons():
	"""Give every Bandhu workspace a desk icon carrying that workspace's own roles.

	`/desk` renders the Desktop Icon grid, not the workspace list, and Frappe seeds icons
	from workspaces only in its `after_app_install` hook — which for this app ran before the
	workspaces declared `app = "bandhu_app"`, so nothing was ever seeded and field staff
	landed on a grid with no route to their own board.
	"""
	app_icon = ensure_app_icon()

	workspaces = frappe.get_all(
		"Workspace",
		filters={"app": "bandhu_app", "public": 1},
		fields=["name", "icon"],
	)
	roles_by_workspace = workspace_roles({workspace.name for workspace in workspaces})

	# A Desktop Icon's link_to is a Dynamic Link resolving against Workspace Sidebar, not
	# Workspace, and the two are synced separately — a workspace whose sidebar row has not
	# been written yet would fail link validation and, from after_migrate, take the whole
	# migrate down with it.
	sidebars = set(frappe.get_all("Workspace Sidebar", pluck="name"))

	for workspace in workspaces:
		if workspace.name not in sidebars:
			frappe.log_error(
				title="No desk icon for workspace",
				message=f"{workspace.name} has no Workspace Sidebar record yet; skipped.",
			)
			continue

		icon_name = frappe.db.get_value(
			"Desktop Icon", {"link_to": workspace.name, "icon_type": "Link"}, "name"
		)
		icon = (
			frappe.get_doc("Desktop Icon", icon_name)
			if icon_name
			else frappe.new_doc("Desktop Icon").update(
				{
					"icon_type": "Link",
					"link_type": "Workspace Sidebar",
					"link_to": workspace.name,
				}
			)
		)
		icon.update(
			{
				"label": workspace.name,
				"icon": workspace.icon,
				"app": "bandhu_app",
				"parent_icon": app_icon,
			}
		)
		# A workspace with no roles is open to every Desk user; mirroring that empty table
		# keeps the icon and the workspace telling the same story.
		icon.set("roles", [{"role": role} for role in roles_by_workspace.get(workspace.name, [])])
		icon.save()


def ensure_app_icon() -> str:
	app_title = frappe.get_hooks("app_title", app_name="bandhu_app")[0]
	existing = frappe.db.get_value("Desktop Icon", {"label": app_title, "icon_type": "App"}, "name")
	if existing:
		return existing

	icon = frappe.new_doc("Desktop Icon")
	icon.update({"label": app_title, "icon_type": "App", "app": "bandhu_app"})
	icon.insert()
	return icon.name


def workspace_roles(workspace_names: set) -> dict:
	rows = frappe.get_all(
		"Has Role",
		filters={"parenttype": "Workspace", "parent": ["in", list(workspace_names)]},
		fields=["parent", "role"],
	)
	roles = {}
	for row in rows:
		roles.setdefault(row.parent, []).append(row.role)
	return roles
