from bandhu_app.bandhu_app.page.staff_onboarding.staff_onboarding import seed_default_genders
from bandhu_app.bandhu_app.utils.clinic_test import seed_default_tests
from bandhu_app.bandhu_app.utils.patient_encounter import seed_default_appointment_type
from bandhu_app.patches.create_helpline_staff_role import execute as create_helpline_staff_role
from bandhu_app.patches.seed_indian_states import execute as seed_indian_states
from bandhu_app.patches.seed_major_sectors import execute as seed_major_sectors
from bandhu_app.patches.stop_linking_customer_to_patient import (
	execute as stop_linking_customer_to_patient,
)


def after_install() -> None:
	seed_default_tests()
	seed_default_genders()
	seed_default_appointment_type()
	seed_indian_states()
	seed_major_sectors()
	stop_linking_customer_to_patient()
	create_helpline_staff_role()
