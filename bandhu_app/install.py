from bandhu_app.bandhu_app.utils.clinic_test import seed_default_tests


def after_install() -> None:
	seed_default_tests()
