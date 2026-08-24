from datetime import datetime

import pytest

from src.patient import Patient, PatientStatus
from src.treatment import TreatmentManager


def make_patient(patient_id):
	return Patient(
		patient_id, "Test", 40, 98, 80, 16, 120, "Normal", "None", 0,
		datetime(2026, 8, 25, 8), 10, False, "GREEN",
	)


def test_capacity_and_start_treatment():
	manager = TreatmentManager(capacity=1)
	first = make_patient("2508-001")
	second = make_patient("2508-002")
	manager.start_treatment(first)
	assert first.status is PatientStatus.IN_TREATMENT
	assert manager.in_treatment_count() == 1
	assert manager.available_slots() == 0
	with pytest.raises(ValueError, match="no treatment slots"):
		manager.start_treatment(second)


def test_non_waiting_patient_cannot_start():
	manager = TreatmentManager()
	patient = make_patient("2508-001")
	patient.status = PatientStatus.COMPLETED
	with pytest.raises(ValueError, match="WAITING"):
		manager.start_treatment(patient)


def test_complete_and_refer_free_slots():
	manager = TreatmentManager(capacity=2)
	completed = make_patient("2508-001")
	referred = make_patient("2508-002")
	manager.start_treatment(completed)
	manager.start_treatment(referred)
	assert manager.complete_treatment(completed.patient_id) is completed
	assert completed.status is PatientStatus.COMPLETED
	assert manager.available_slots() == 1
	assert manager.refer_patient(referred.patient_id) is referred
	assert referred.status is PatientStatus.REFERRED
	assert manager.available_slots() == 2
	assert manager.get_in_treatment_patients() == []


@pytest.mark.parametrize("capacity", [0, -1, 1.5, float("nan"), True])
def test_capacity_must_be_a_positive_integer(capacity):
	with pytest.raises(ValueError, match="positive integer"):
		TreatmentManager(capacity)


@pytest.mark.parametrize("capacity", [1, 3])
def test_positive_integer_capacity_is_accepted(capacity):
	assert TreatmentManager(capacity).available_slots() == capacity
