"""Triage scoring components for Smart Medic."""

from .patient import Patient


ScoreBreakdown = dict[str, int]


def spo2_contribution(spo2: int) -> int:
	"""Return the SpO2 contribution, bounded from 0 through 20."""
	if spo2 >= 95:
		return 0
	if spo2 >= 92:
		return 5
	if spo2 >= 88:
		return 12
	if spo2 >= 84:
		return 17
	return 20


def systolic_bp_contribution(systolic_bp: int) -> int:
	"""Return the systolic blood pressure contribution, bounded from 0 through 15."""
	if systolic_bp < 80:
		return 15
	if systolic_bp < 90:
		return 10
	if systolic_bp < 100:
		return 5
	if systolic_bp <= 139:
		return 0
	if systolic_bp <= 159:
		return 2
	return 4


def respiratory_rate_contribution(respiratory_rate: int) -> int:
	"""Return the respiratory rate contribution, bounded from 0 through 15."""
	if respiratory_rate < 12:
		return 10
	if respiratory_rate <= 20:
		return 0
	if respiratory_rate <= 24:
		return 4
	if respiratory_rate <= 30:
		return 9
	return 15


def heart_rate_contribution(heart_rate: int) -> int:
	"""Return the heart rate contribution, bounded from 0 through 10."""
	if heart_rate < 60:
		return 5
	if heart_rate <= 100:
		return 0
	if heart_rate <= 110:
		return 2
	if heart_rate <= 130:
		return 5
	if heart_rate <= 150:
		return 8
	return 10


def consciousness_contribution(consciousness: str) -> int:
	"""Return the consciousness contribution, bounded from 0 through 15."""
	return {
		"Normal": 0,
		"Moderate": 7,
		"Severe": 12,
		"Unresponsive": 15,
	}[consciousness]


def bleeding_contribution(bleeding: str) -> int:
	"""Return the bleeding contribution, bounded from 0 through 14."""
	return {
		"None": 0,
		"Mild": 3,
		"Moderate": 7,
		"Severe": 14,
	}[bleeding]


def pain_contribution(pain_level: int) -> int:
	"""Return the pain contribution, bounded from 0 through 5."""
	if pain_level <= 2:
		return 0
	if pain_level <= 4:
		return 1
	if pain_level <= 6:
		return 2
	if pain_level <= 8:
		return 4
	return 5


def age_contribution(age: int) -> int:
	"""Return the age contribution, bounded from 0 through 5."""
	if age <= 64:
		return 0
	if age <= 74:
		return 2
	return 5


def get_score_breakdown(patient: Patient) -> ScoreBreakdown:
	"""Return the base score and each clinical score contribution."""
	return {
		"base": 1,
		"spo2": spo2_contribution(patient.spo2),
		"systolic_bp": systolic_bp_contribution(patient.systolic_bp),
		"respiratory_rate": respiratory_rate_contribution(patient.respiratory_rate),
		"heart_rate": heart_rate_contribution(patient.heart_rate),
		"consciousness": consciousness_contribution(patient.consciousness),
		"bleeding": bleeding_contribution(patient.bleeding),
		"pain": pain_contribution(patient.pain_level),
		"age": age_contribution(patient.age),
	}


def calculate_score(patient: Patient) -> int:
	"""Calculate the complete clinical priority score from 1 through 100."""
	return sum(get_score_breakdown(patient).values())