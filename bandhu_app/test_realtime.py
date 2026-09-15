from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from bandhu_app.bandhu_app.utils.realtime import (
	BOARD_UPDATE_DOCTYPE,
	BOARD_UPDATE_EVENT,
	broadcast_encounter_change,
	publish_board_update,
)

PUBLISH = "bandhu_app.bandhu_app.utils.realtime.frappe.publish_realtime"


class TestBoardUpdates(IntegrationTestCase):
	def test_update_goes_to_the_session_document_room_after_commit(self):
		with self.set_user("Administrator"), patch(PUBLISH) as publish_realtime:
			publish_board_update("CS-TEST-0001")

		publish_realtime.assert_called_once_with(
			BOARD_UPDATE_EVENT,
			{"clinic_session": "CS-TEST-0001", "actor": "Administrator"},
			doctype=BOARD_UPDATE_DOCTYPE,
			docname="CS-TEST-0001",
			after_commit=True,
		)

	def test_no_update_without_a_session(self):
		with patch(PUBLISH) as publish_realtime:
			publish_board_update(None)
			publish_board_update("")

		publish_realtime.assert_not_called()

	def test_encounter_change_publishes_to_its_own_session(self):
		encounter = frappe._dict(custom_clinic_session="CS-TEST-0002")

		with patch(PUBLISH) as publish_realtime:
			broadcast_encounter_change(encounter)

		self.assertEqual(publish_realtime.call_args.kwargs["docname"], "CS-TEST-0002")
