from datetime import datetime

import pytest

from src.patient import Patient
from src.triage import check_red_flags, classify_triage


def make_patient(**changes):
	values = dict(
		patient_id="2508-001", name="Test", age=40, spo2=98, heart_rate=80,
		respiratory_rate=16, systolic_bp=120, consciousness="Normal",
		bleeding="None", pain_level=0, arrival_time=datetime(2026, 8, 25, 8),
		clinical_score=10, triage_level="GREEN",
	)
	values.update(changes)
	return Patient(**values)


@pytest.mark.parametrize(
	"changes, reason",
	[
		({"consciousness": "Unresponsive"}, "Unresponsive"),
		({"bleeding": "Severe"}, "Severe bleeding"),
		({"heart_rate": 49}, "Extreme heart rate"),
		({"spo2": 87}, "Extremely low SpO2"),
		({"systolic_bp": 79}, "Severely low systolic blood pressure"),
		({"consciousness": "Severe", "heart_rate": 59}, "Severe consciousness with major vital abnormality"),
	],
)
def test_red_flag_rules(changes, reason):
	result = check_red_flags(make_patient(**changes))
	assert result.red_flag is True
	assert result.reason == reason


def test_no_red_flag_and_classification_threshold():
	patient = make_patient()
	assert check_red_flags(patient).red_flag is False
	assert classify_triage(patient, clinical_score=39).triage_level == "GREEN"
	assert classify_triage(patient, clinical_score=40).triage_level == "YELLOW"


def test_red_overrides_score_level():
	result = classify_triage(make_patient(heart_rate=49), clinical_score=1)
	assert result.triage_level == "RED"
	assert result.red_flag is True
