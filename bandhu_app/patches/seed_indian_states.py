import frappe

# The CAD registration form's Native State "Other" picker only ever offered Kerala --
# the 6 major-source states plus Kerala were the only State records that existed,
# so a patient from anywhere else in India had no valid value to select at all.
OTHER_STATES = [
	"Andhra Pradesh",
	"Arunachal Pradesh",
	"Chhattisgarh",
	"Goa",
	"Gujarat",
	"Haryana",
	"Himachal Pradesh",
	"Jharkhand",
	"Karnataka",
	"Madhya Pradesh",
	"Maharashtra",
	"Manipur",
	"Meghalaya",
	"Mizoram",
	"Nagaland",
	"Punjab",
	"Rajasthan",
	"Sikkim",
	"Telangana",
	"Tripura",
	"Uttarakhand",
	"Andaman and Nicobar Islands",
	"Chandigarh",
	"Dadra and Nagar Haveli and Daman and Diu",
	"Delhi",
	"Jammu and Kashmir",
	"Ladakh",
	"Lakshadweep",
	"Puducherry",
]


def execute():
	if not frappe.db.has_column("State", "is_major_state"):
		return

	for state_name in OTHER_STATES:
		if frappe.db.exists("State", state_name):
			continue
		frappe.get_doc(
			{
				"doctype": "State",
				"state_name": state_name,
				"country": "India",
				"is_major_state": 0,
			}
		).insert(ignore_permissions=True)
