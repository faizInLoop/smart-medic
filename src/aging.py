"""Queue aging components for Smart Medic."""

from datetime import datetime

from .patient import Patient, PatientStatus


def calculate_waiting_minutes(
	arrival_time: datetime, current_time: datetime
) -> int:
	"""Return completed waiting minutes between two timestamps."""
	seconds_waiting = (current_time - arrival_time).total_seconds()
	return max(0, int(seconds_waiting // 60))


def calculate_aging_adjustment(waiting_minutes: int) -> int:
	"""Return capped aging points for completed post-30-minute intervals."""
	if waiting_minutes <= 30:
		return 0
	completed_intervals = (waiting_minutes - 30) // 10
	return min(20, completed_intervals * 2)


def apply_aging(patient: Patient, current_time: datetime) -> int:
	"""Update a patient's active aging and queue priority, returning the adjustment."""
	if patient.status is not PatientStatus.WAITING:
		patient.aging_adjustment = 0
		patient.queue_priority = None
		return 0

	waiting_minutes = calculate_waiting_minutes(patient.arrival_time, current_time)
	patient.aging_adjustment = calculate_aging_adjustment(waiting_minutes)
	if patient.clinical_score is None:
		patient.queue_priority = None
	else:
		patient.queue_priority = patient.clinical_score + patient.aging_adjustment
	return patient.aging_adjustment