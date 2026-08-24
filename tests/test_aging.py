from datetime import datetime, timedelta

import pytest

from src.aging import apply_aging, calculate_aging_adjustment, calculate_waiting_minutes
from src.patient import Patient, PatientStatus


@pytest.mark.parametrize("minutes, expected", [(0, 0), (29, 0), (30, 0), (39, 0), (40, 2), (60, 6), (130, 20), (150, 20)])
def test_aging_intervals(minutes, expected):
	assert calculate_aging_adjustment(minutes) == expected


def make_patient(arrival_time):
	return Patient(
		"2508-001", "Test", 40, 98, 80, 16, 120, "Normal", "None", 0,
		arrival_time, 35, False, "GREEN",
	)


def test_waiting_time_and_patient_specific_aging():
	now = datetime(2026, 8, 25, 10)
	patient = make_patient(now - timedelta(minutes=40))
	other = make_patient(now - timedelta(minutes=60))
	assert calculate_waiting_minutes(patient.arrival_time, now) == 40
	assert apply_aging(patient, now) == 2
	assert apply_aging(other, now) == 6
	assert patient.queue_priority == 37
	assert other.queue_priority == 41


def test_non_waiting_patient_has_no_active_aging():
	patient = make_patient(datetime(2026, 8, 25, 8))
	patient.status = PatientStatus.COMPLETED
	patient.aging_adjustment = 20
	patient.queue_priority = 55
	assert apply_aging(patient, datetime(2026, 8, 25, 12)) == 0
	assert patient.aging_adjustment == 0
	assert patient.queue_priority is None
