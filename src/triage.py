"""Emergency triage components for Smart Medic."""

from dataclasses import dataclass

from .patient import Patient
from .scoring import calculate_score


@dataclass(frozen=True)
class RedFlagResult:
	"""Result of red-flag evaluation, including an explanation when present."""

	red_flag: bool
	reason: str | None = None


@dataclass(frozen=True)
class TriageResult:
	"""Triage level, clinical score, and red-flag evaluation result."""

	triage_level: str
	clinical_score: int
	red_flag: bool
	reason: str | None = None


def check_red_flags(patient: Patient) -> RedFlagResult:
	"""Check the defined adult-prototype red-flag rules in order."""
	if patient.consciousness == "Unresponsive":
		return RedFlagResult(True, "Unresponsive")
	if patient.bleeding == "Severe":
		return RedFlagResult(True, "Severe bleeding")
	if patient.heart_rate < 50 or patient.heart_rate > 150:
		return RedFlagResult(True, "Extreme heart rate")
	if patient.spo2 < 88:
		return RedFlagResult(True, "Extremely low SpO2")
	if patient.systolic_bp < 80:
		return RedFlagResult(True, "Severely low systolic blood pressure")
	if patient.consciousness == "Severe" and (
		patient.spo2 < 92
		or patient.systolic_bp < 90
		or patient.respiratory_rate < 10
		or patient.respiratory_rate > 30
		or patient.heart_rate < 60
		or patient.heart_rate > 130
	):
		return RedFlagResult(True, "Severe consciousness with major vital abnormality")
	return RedFlagResult(False)


def classify_triage(
	patient: Patient, clinical_score: int | None = None
) -> TriageResult:
	"""Return RED, YELLOW, or GREEN using red flags and the clinical score."""
	score = calculate_score(patient) if clinical_score is None else clinical_score
	red_flag_result = check_red_flags(patient)
	if red_flag_result.red_flag:
		triage_level = "RED"
	elif score >= 40:
		triage_level = "YELLOW"
	else:
		triage_level = "GREEN"
	return TriageResult(
		triage_level=triage_level,
		clinical_score=score,
		red_flag=red_flag_result.red_flag,
		reason=red_flag_result.reason,
	)