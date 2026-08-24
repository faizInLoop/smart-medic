"""Patient reassessment components for Smart Medic."""

from dataclasses import dataclass

from .patient import Patient, PatientStatus
from .scoring import calculate_score
from .triage import classify_triage
from .validation import (
	validate_bleeding,
	validate_consciousness,
	validate_heart_rate,
	validate_pain_level,
	validate_respiratory_rate,
	validate_spo2,
	validate_systolic_bp,
)


@dataclass(frozen=True)
class ReassessmentResult:
	"""Report clinical and triage changes produced by reassessment."""

	patient_id: str
	previous_score: int | None
	new_score: int
	previous_triage_level: str | None
	new_triage_level: str
	previous_red_flag: bool
	new_red_flag: bool
	red_flag_reason: str | None
	changed_fields: tuple[str, ...]


def reassess_patient(
	patient: Patient,
	spo2: object,
	heart_rate: object,
	respiratory_rate: object,
	systolic_bp: object,
	consciousness: object,
	bleeding: object,
	pain_level: object,
) -> ReassessmentResult:
	"""Apply validated clinical updates to a waiting patient and recalculate triage."""
	if patient.status is not PatientStatus.WAITING:
		raise ValueError(
			"reassessment is only allowed for patients with WAITING status"
		)

	validated_values = {
		"spo2": validate_spo2(spo2),
		"heart_rate": validate_heart_rate(heart_rate),
		"respiratory_rate": validate_respiratory_rate(respiratory_rate),
		"systolic_bp": validate_systolic_bp(systolic_bp),
		"consciousness": validate_consciousness(consciousness),
		"bleeding": validate_bleeding(bleeding),
		"pain_level": validate_pain_level(pain_level),
	}
	changed_fields = tuple(
		field_name
		for field_name, new_value in validated_values.items()
		if getattr(patient, field_name) != new_value
	)
	previous_score = patient.clinical_score
	previous_triage_level = patient.triage_level
	previous_red_flag = patient.red_flag

	for field_name, new_value in validated_values.items():
		setattr(patient, field_name, new_value)

	new_score = calculate_score(patient)
	triage_result = classify_triage(patient, clinical_score=new_score)
	patient.clinical_score = new_score
	patient.red_flag = triage_result.red_flag
	patient.triage_level = triage_result.triage_level
	patient.red_flag_reason = triage_result.reason
	patient.aging_adjustment = 0
	patient.queue_priority = new_score

	return ReassessmentResult(
		patient_id=patient.patient_id,
		previous_score=previous_score,
		new_score=new_score,
		previous_triage_level=previous_triage_level,
		new_triage_level=triage_result.triage_level,
		previous_red_flag=previous_red_flag,
		new_red_flag=triage_result.red_flag,
		red_flag_reason=triage_result.reason,
		changed_fields=changed_fields,
	)