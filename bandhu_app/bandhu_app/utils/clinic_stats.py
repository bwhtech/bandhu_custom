import frappe

COMPLETED_STATE = "Completed"


def count_encounters(session_names: list) -> dict:
	rows = frappe.db.sql(
		"""
		select
			custom_clinic_session as session,
			count(*) as patients,
			sum(case when custom_workflow_state = %(completed)s then 1 else 0 end) as completed
		from `tabPatient Encounter`
		where docstatus < 2 and custom_clinic_session in %(sessions)s
		group by custom_clinic_session
		""",
		{"sessions": session_names, "completed": COMPLETED_STATE},
		as_dict=True,
	)
	return {row.session: row for row in rows}


def count_new_patients(session_names: list) -> dict:
	"""A patient is new when this camp holds their first encounter anywhere in the system."""
	rows = frappe.db.sql(
		"""
		select encounter.custom_clinic_session as session, count(*) as new_patients
		from `tabPatient Encounter` encounter
		where encounter.docstatus < 2
			and encounter.custom_clinic_session in %(sessions)s
			and not exists (
				select 1 from `tabPatient Encounter` earlier
				where earlier.patient = encounter.patient
					and earlier.docstatus < 2
					and earlier.creation < encounter.creation
			)
		group by encounter.custom_clinic_session
		""",
		{"sessions": session_names},
		as_dict=True,
	)
	return {row.session: row.new_patients for row in rows}


def count_tests(session_names: list) -> dict:
	"""Tests live on the encounter's `custom_test_instructions` child table, not on the
	`Test Result` doctype — nothing in the clinic loop writes that doctype."""
	rows = frappe.db.sql(
		"""
		select
			encounter.custom_clinic_session as session,
			count(*) as ordered,
			sum(case when ifnull(test.result_type, '') != '' then 1 else 0 end) as done
		from `tabTest Instructions` test
		inner join `tabPatient Encounter` encounter on encounter.name = test.parent
		where test.parenttype = 'Patient Encounter'
			and encounter.docstatus < 2
			and encounter.custom_clinic_session in %(sessions)s
		group by encounter.custom_clinic_session
		""",
		{"sessions": session_names},
		as_dict=True,
	)
	return {row.session: row for row in rows}


def count_medicines(session_names: list) -> dict:
	rows = frappe.db.sql(
		"""
		select
			encounter.custom_clinic_session as session,
			count(*) as prescribed,
			sum(case when prescription.dispensed = 1 then 1 else 0 end) as dispensed
		from `tabPrescription` prescription
		inner join `tabPatient Encounter` encounter on encounter.name = prescription.parent
		where prescription.parenttype = 'Patient Encounter'
			and encounter.docstatus < 2
			and encounter.custom_clinic_session in %(sessions)s
		group by encounter.custom_clinic_session
		""",
		{"sessions": session_names},
		as_dict=True,
	)
	return {row.session: row for row in rows}
