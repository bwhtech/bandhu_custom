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
	"""Put one Bandhu App tile on /desk, visible to the roles our workspaces are for.

	/desk renders the Desktop Icon grid, not the workspace list, and Frappe seeds icons from
	workspaces only in its `after_app_install` hook — which for this app ran before the
	workspaces declared `app = "bandhu_app"`, so nothing was ever seeded and field staff
	landed on a grid with no route to their own board.

	One icon, not one per workspace: `is_icon_permitted` resolves a link icon through
	`bootinfo.workspace_sidebar_item`, which is keyed by app ("bandhu app"), never by
	workspace name, so per-workspace icons are created and then filtered straight back out.
	The app tile is the route; the sidebar behind it is already role-filtered per workspace.
	"""
	app_title = frappe.get_hooks("app_title", app_name="bandhu_app")[0]
	icon_name = frappe.db.get_value("Desktop Icon", {"label": app_title, "icon_type": "App"}, "name")
	icon = (
		frappe.get_doc("Desktop Icon", icon_name)
		if icon_name
		else frappe.new_doc("Desktop Icon").update({"label": app_title, "icon_type": "App"})
	)
	icon.app = "bandhu_app"

	# Without a roles table the tile shows to every Desk user on the site, who would click
	# into an empty sidebar. The union of what our workspaces are for is exactly who has
	# something behind it.
	roles = workspace_roles()
	icon.set("roles", [{"role": role} for role in sorted(roles)])
	icon.save()


def workspace_roles() -> set:
	workspaces = frappe.get_all("Workspace", filters={"app": "bandhu_app", "public": 1}, pluck="name")
	return set(
		frappe.get_all(
			"Has Role",
			filters={"parenttype": "Workspace", "parent": ["in", workspaces]},
			pluck="role",
		)
	)
