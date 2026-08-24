from datetime import datetime

import pytest

from src.patient import Patient
from src.scoring import (
	age_contribution,
	bleeding_contribution,
	calculate_score,
	consciousness_contribution,
	get_score_breakdown,
	heart_rate_contribution,
	pain_contribution,
	respiratory_rate_contribution,
	spo2_contribution,
	systolic_bp_contribution,
)


@pytest.mark.parametrize("value, expected", [(95, 0), (94, 5), (91, 12), (87, 17), (83, 20)])
def test_spo2_boundaries(value, expected):
	assert spo2_contribution(value) == expected


@pytest.mark.parametrize("value, expected", [(79, 15), (80, 10), (90, 5), (100, 0), (140, 2), (160, 4)])
def test_systolic_bp_boundaries(value, expected):
	assert systolic_bp_contribution(value) == expected


@pytest.mark.parametrize("value, expected", [(11, 10), (12, 0), (21, 4), (25, 9), (31, 15)])
def test_respiratory_rate_boundaries(value, expected):
	assert respiratory_rate_contribution(value) == expected


@pytest.mark.parametrize("value, expected", [(59, 5), (60, 0), (101, 2), (111, 5), (131, 8), (151, 10)])
def test_heart_rate_boundaries(value, expected):
	assert heart_rate_contribution(value) == expected


def test_categorical_and_age_contributions():
	assert [consciousness_contribution(value) for value in ("Normal", "Moderate", "Severe", "Unresponsive")] == [0, 7, 12, 15]
	assert [bleeding_contribution(value) for value in ("None", "Mild", "Moderate", "Severe")] == [0, 3, 7, 14]
	assert [pain_contribution(value) for value in (2, 3, 5, 7, 9)] == [0, 1, 2, 4, 5]
	assert [age_contribution(value) for value in (18, 64, 65, 74, 75)] == [0, 0, 2, 2, 5]


def test_score_is_bounded_and_breakdown_sums_to_total():
	patient = Patient(
		"2508-001", "Test", 95, 83, 151, 31, 79, "Unresponsive", "Severe", 10,
		datetime(2026, 8, 25, 8),
	)
	breakdown = get_score_breakdown(patient)
	assert calculate_score(patient) == 100
	assert sum(breakdown.values()) == 100
