from datetime import datetime, timedelta

import pytest

from src.patient import Patient, PatientStatus
from src.queue_manager import PriorityQueueManager


def make_patient(patient_id, level, score, priority, minutes=0):
	return Patient(
		patient_id, "Test", 40, 98, 80, 16, 120, "Normal", "None", 0,
		datetime(2026, 8, 25, 8) + timedelta(minutes=minutes), score, False,
		level, 0, priority,
	)


def test_priority_level_score_and_tie_ordering():
	queue = PriorityQueueManager()
	red = make_patient("2508-001", "RED", 1, 1, 5)
	yellow_high = make_patient("2508-002", "YELLOW", 25, 45)
	yellow_low = make_patient("2508-003", "YELLOW", 30, 30)
	green = make_patient("2508-004", "GREEN", 100, 100)
	for patient in (green, yellow_low, yellow_high, red):
		queue.add_patient(patient)
	assert [patient.patient_id for patient in queue.get_waiting_patients()] == [
		"2508-001", "2508-002", "2508-003", "2508-004"
	]

	first = make_patient("2508-005", "GREEN", 20, 20, 10)
	second = make_patient("2508-006", "GREEN", 20, 20, 10)
	tie_queue = PriorityQueueManager()
	tie_queue.add_patient(second)
	tie_queue.add_patient(first)
	assert tie_queue.peek_next() is first


def test_update_patient_reorders_existing_entry():
	queue = PriorityQueueManager()
	first = make_patient("2508-001", "YELLOW", 30, 30)
	second = make_patient("2508-002", "YELLOW", 25, 45, 1)
	queue.add_patient(first)
	queue.add_patient(second)
	first.queue_priority = 60
	queue.update_patient(first)
	assert queue.peek_next() is first
	first.queue_priority = 10
	queue.update_patient(first)
	assert queue.peek_next() is second


def test_pop_remove_and_missing_priority():
	queue = PriorityQueueManager()
	patient = make_patient("2508-001", "GREEN", 10, 10)
	queue.add_patient(patient)
	assert queue.remove_patient(patient.patient_id) is True
	assert queue.is_empty()
	assert queue.remove_patient(patient.patient_id) is False

	patient.queue_priority = None
	with pytest.raises(ValueError, match="queue priority"):
		queue.add_patient(patient)


def test_pop_marks_patient_in_treatment():
	queue = PriorityQueueManager()
	patient = make_patient("2508-001", "GREEN", 10, 10)
	queue.add_patient(patient)
	assert queue.pop_next() is patient
	assert patient.status is PatientStatus.IN_TREATMENT
	assert queue.pop_next() is None


@pytest.mark.parametrize("patient_id", ["abcd-001", "2508-01", "2508-0001", "2508", "250801"])
def test_patient_id_must_use_strict_format(patient_id):
	patient = make_patient(patient_id, "GREEN", 10, 10)
	with pytest.raises(ValueError, match="DDMM-NNN"):
		PriorityQueueManager().add_patient(patient)


def test_valid_patient_id_format_is_accepted():
	queue = PriorityQueueManager()
	queue.add_patient(make_patient("2508-001", "GREEN", 10, 10))
	assert len(queue) == 1
