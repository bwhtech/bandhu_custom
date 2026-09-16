from bandhu_app.bandhu_app.utils.clinic_test import seed_default_tests
from bandhu_app.bandhu_app.utils.patient_encounter import seed_default_appointment_type
from bandhu_app.patches.seed_indian_states import execute as seed_indian_states
from bandhu_app.patches.seed_major_sectors import execute as seed_major_sectors
from bandhu_app.patches.seed_offered_genders import execute as seed_offered_genders
from bandhu_app.patches.stop_linking_customer_to_patient import (
	execute as stop_linking_customer_to_patient,
)


def after_install() -> None:
	seed_default_tests()
	seed_offered_genders()
	seed_default_appointment_type()
	seed_indian_states()
	seed_major_sectors()
	stop_linking_customer_to_patient()
