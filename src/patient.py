"""Patient data structures for Smart Medic."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PatientStatus(Enum):
	"""Operational status of a patient."""

	WAITING = "WAITING"
	IN_TREATMENT = "IN_TREATMENT"
	COMPLETED = "COMPLETED"
	REFERRED = "REFERRED"


@dataclass
class Patient:
	"""Store patient identity and clinical input, triage, and queue state."""

	patient_id: str
	name: str
	age: int
	spo2: int
	heart_rate: int
	respiratory_rate: int
	systolic_bp: int
	consciousness: str
	bleeding: str
	pain_level: int
	arrival_time: datetime
	clinical_score: int | None = None
	red_flag: bool = False
	triage_level: str | None = None
	aging_adjustment: int = 0
	queue_priority: int | None = None
	status: PatientStatus = PatientStatus.WAITING
	internal_record_id: str | None = None
	treatment_start_time: datetime | None = None
	exit_time: datetime | None = None
	red_flag_reason: str | None = None