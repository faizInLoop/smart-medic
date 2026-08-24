from datetime import datetime

import pytest

from src.patient import Patient, PatientStatus
from src.reassessment import reassess_patient


def make_patient():
	return Patient(
		"2508-001", "Test", 40, 98, 80, 16, 120, "Normal", "None", 0,
		datetime(2026, 8, 25, 8), 1, False, "GREEN", 4, 5,
	)


def test_reassessment_updates_clinical_and_triage_state():
	patient = make_patient()
	arrival_time = patient.arrival_time
	result = reassess_patient(patient, 87, 151, 31, 79, "Unresponsive", "Severe", 10)
	assert result.patient_id == "2508-001"
	assert result.previous_score == 1
	assert result.new_score != 1
	assert result.previous_triage_level == "GREEN"
	assert result.new_triage_level == "RED"
	assert result.new_red_flag is True
	assert result.red_flag_reason == "Unresponsive"
	assert patient.red_flag_reason == "Unresponsive"
	assert set(result.changed_fields) == {
		"spo2", "heart_rate", "respiratory_rate", "systolic_bp",
		"consciousness", "bleeding", "pain_level",
	}
	assert patient.patient_id == "2508-001"
	assert patient.arrival_time == arrival_time
	assert patient.aging_adjustment == 0
	assert patient.queue_priority == patient.clinical_score


def test_invalid_reassessment_does_not_mutate_patient():
	patient = make_patient()
	original = patient.spo2
	with pytest.raises(ValueError):
		reassess_patient(patient, None, 80, 16, 120, "Normal", "None", 0)
	assert patient.spo2 == original


def test_reassessment_requires_waiting_status():
	patient = make_patient()
	patient.status = PatientStatus.IN_TREATMENT
	with pytest.raises(ValueError, match="WAITING"):
		reassess_patient(patient, 98, 80, 16, 120, "Normal", "None", 0)


def test_reassessment_clears_reason_when_patient_is_no_longer_red():
	patient = make_patient()
	patient.red_flag = True
	patient.red_flag_reason = "Unresponsive"
	reassess_patient(patient, 98, 80, 16, 120, "Normal", "None", 0)
	assert patient.red_flag is False
	assert patient.red_flag_reason is None
