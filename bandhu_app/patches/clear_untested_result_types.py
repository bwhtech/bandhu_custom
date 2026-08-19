import frappe


def execute():
	"""Tests that were only ordered are stored as `result_type = "Positive"`.

	`Test Instructions.result_type` had no blank first option, so Frappe filled every
	newly ordered test row with the first Select value. A malaria test nobody has run
	yet therefore reads as positive on any board or report. The schema now starts the
	options with a blank; this clears the rows the old schema mislabelled.

	Only rows whose encounter is still awaiting its test are touched — once the nurse
	has submitted, `result_type` is the value they chose and must not be rewritten.
	"""
	frappe.db.sql(
		"""
		update `tabTest Instructions` test
		inner join `tabPatient Encounter` encounter on encounter.name = test.parent
		set test.result_type = ''
		where test.parenttype = 'Patient Encounter'
			and encounter.custom_workflow_state = 'Awaiting Test'
			and ifnull(test.result_value, '') = ''
		"""
	)
