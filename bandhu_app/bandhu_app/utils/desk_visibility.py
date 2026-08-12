import frappe

# Framework (frappe), Quality (erpnext) and Marley Health (healthcare) ship their
# own Desktop Icon on the /desk app grid with no role restriction, so every
# Desk user sees them regardless of app relevance. We don't own those apps'
# fixtures (never edit apps/frappe, apps/erpnext — lost on bench update), and
# each app's own `bench migrate` re-syncs its Desktop Icon from its own JSON on
# every run, silently wiping any restriction set directly on the doc. Running
# this again after every migrate, via the after_migrate hook, is what makes it
# stick.
OTHER_APP_DESKTOP_ICONS_TO_RESTRICT = ["Framework", "Quality", "Marley Health"]
ALLOWED_ROLES = ["System Manager"]


def restrict_other_app_desktop_icons():
	for icon_name in OTHER_APP_DESKTOP_ICONS_TO_RESTRICT:
		if not frappe.db.exists("Desktop Icon", icon_name):
			continue

		icon = frappe.get_doc("Desktop Icon", icon_name)
		current_roles = {row.role for row in icon.roles}
		if current_roles == set(ALLOWED_ROLES):
			continue

		icon.set("roles", [{"role": role} for role in ALLOWED_ROLES])
		icon.save()
