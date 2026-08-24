"""Deterministic orchestration for a Smart Medic clinic workflow."""

from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

from .aging import apply_aging
from .data_loader import load_patients_from_csv
from .patient import Patient, PatientStatus
from .queue_manager import PriorityQueueManager
from .reassessment import ReassessmentResult, reassess_patient
from .treatment import TreatmentManager


class SmartMedicSimulation:
	"""Coordinate loading, waiting, reassessment, and treatment operations."""

	def __init__(
		self,
		capacity: int = 3,
		current_time: datetime | None = None,
		treatment_duration_minutes: int = 20,
		automatic_treatment: bool = False,
	) -> None:
		if (
			isinstance(treatment_duration_minutes, bool)
			or not isinstance(treatment_duration_minutes, int)
			or treatment_duration_minutes <= 0
		):
			raise ValueError("treatment duration must be a positive integer")
		self.queue = PriorityQueueManager()
		self.treatment = TreatmentManager(capacity)
		self.current_time = current_time
		self.treatment_duration_minutes = treatment_duration_minutes
		self.automatic_treatment = automatic_treatment
		self._patients: dict[str, Patient] = {}
		self._queued_ids: set[str] = set()
		self._next_sequence_by_date: defaultdict[object, int] = defaultdict(int)

	def load_patients(self, path: str | Path) -> list[Patient]:
		"""Load patients from CSV and place their WAITING records in the queue."""
		patients = load_patients_from_csv(
			path,
			current_time=self.current_time,
			assign_future_ids=False,
		)
		self.queue = PriorityQueueManager()
		self.treatment = TreatmentManager(self.treatment.capacity)
		self._patients = {
			patient.internal_record_id or patient.patient_id: patient
			for patient in patients
		}
		self._queued_ids = set()
		self._next_sequence_by_date = defaultdict(int)
		if self.current_time is None and patients:
			self.current_time = min(patient.arrival_time for patient in patients)
		current_time = self.current_time
		if current_time is None:
			return patients
		for patient in patients:
			if patient.arrival_time <= current_time:
				self._assign_public_id(patient)
				self.queue.add_patient(patient)
				self._queued_ids.add(patient.patient_id)
		if self.automatic_treatment:
			self._fill_treatment_slots()
		return patients

	def advance_time(self, minutes: int) -> datetime:
		"""Advance the clock and refresh aging for every waiting patient."""
		if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 0:
			raise ValueError("minutes must be a non-negative integer")
		if self.current_time is None:
			raise ValueError("simulation current_time is not initialized")
		current_time = self.current_time
		target_time = current_time + timedelta(minutes=minutes)
		if self.automatic_treatment:
			self._process_events_until(target_time)
		else:
			self.current_time = target_time
			self._refresh_waiting_patients()
			self._admit_arrived_patients()
		return self.current_time

	def reassess_patient(
		self,
		patient_id: str,
		spo2: object,
		heart_rate: object,
		respiratory_rate: object,
		systolic_bp: object,
		consciousness: object,
		bleeding: object,
		pain_level: object,
	) -> ReassessmentResult:
		"""Reassess a waiting patient and refresh its queue entry."""
		patient = self._get_patient(patient_id)
		if patient.status is PatientStatus.WAITING and patient.patient_id not in self._queued_ids:
			raise ValueError(
				"reassessment is only allowed for patients currently in the waiting queue"
			)
		result = reassess_patient(
			patient,
			spo2,
			heart_rate,
			respiratory_rate,
			systolic_bp,
			consciousness,
			bleeding,
			pain_level,
		)
		self.queue.update_patient(patient)
		return result

	def call_next(self) -> Patient | None:
		"""Start treatment for the highest-priority waiting patient."""
		patient = self.queue.peek_next()
		if patient is None:
			return None
		if not self.queue.remove_patient(patient.patient_id):
			raise RuntimeError(
				"could not remove called patient from the waiting queue"
			)
		self._queued_ids.discard(patient.patient_id)
		try:
			self.treatment.start_treatment(patient)
			patient.treatment_start_time = self.current_time
		except ValueError as error:
			try:
				self.queue.add_patient(patient)
				self._queued_ids.add(patient.patient_id)
			except Exception as restore_error:
				raise RuntimeError(
					"could not start treatment or restore patient to the waiting queue"
				) from restore_error
			raise error
		return patient

	def complete_treatment(self, patient_id: str) -> Patient:
		"""Complete treatment through the treatment manager."""
		patient = self.treatment.complete_treatment(patient_id)
		patient.exit_time = self.current_time
		if self.automatic_treatment:
			self._fill_treatment_slots()
		return patient

	def refer_patient(self, patient_id: str) -> Patient:
		"""Refer a patient through the treatment manager."""
		patient = self.treatment.refer_patient(patient_id)
		patient.exit_time = self.current_time
		if self.automatic_treatment:
			self._fill_treatment_slots()
		return patient

	def get_waiting_patients(self) -> list[Patient]:
		"""Return the current waiting queue in priority order."""
		return self.queue.get_waiting_patients()

	def get_in_treatment_patients(self) -> list[Patient]:
		"""Return patients currently in treatment."""
		return self.treatment.get_in_treatment_patients()

	def get_performance_metrics(self) -> dict[str, float | int]:
		"""Return waiting, turnaround, and served metrics for exited patients."""
		exited = [
			patient
			for patient in self._patients.values()
			if patient.exit_time is not None
			and patient.treatment_start_time is not None
		]
		waiting_times: list[float] = []
		turnaround_times: list[float] = []
		for patient in exited:
			start_time = patient.treatment_start_time
			exit_time = patient.exit_time
			if start_time is None or exit_time is None:
				continue
			waiting_times.append((start_time - patient.arrival_time).total_seconds() / 60)
			turnaround_times.append((exit_time - patient.arrival_time).total_seconds() / 60)
		return {
			"average_waiting_minutes": sum(waiting_times) / len(waiting_times)
			if waiting_times
			else 0.0,
			"average_turnaround_minutes": sum(turnaround_times) / len(turnaround_times)
			if turnaround_times
			else 0.0,
			"patients_served": len(exited),
		}

	def _get_patient(self, patient_id: str) -> Patient:
		patient = self._patients.get(patient_id)
		if patient is not None:
			return patient
		for patient in self._patients.values():
			if patient.patient_id == patient_id:
				return patient
		raise ValueError(f"patient {patient_id!r} was not found")

	def _assign_public_id(self, patient: Patient) -> None:
		if patient.patient_id and not patient.patient_id.startswith("scheduled-"):
			date_key = patient.arrival_time.date()
			sequence = int(patient.patient_id.rsplit("-", 1)[1])
			self._next_sequence_by_date[date_key] = max(
				self._next_sequence_by_date[date_key], sequence
			)
			return
		date_key = patient.arrival_time.date()
		self._next_sequence_by_date[date_key] += 1
		patient.patient_id = (
			f"{patient.arrival_time:%d%m}-"
			f"{self._next_sequence_by_date[date_key]:03d}"
		)

	def _complete_due_treatments(self) -> None:
		if self.current_time is None:
			return
		for patient in list(self.treatment.get_in_treatment_patients()):
			if (
				patient.treatment_start_time is not None
				and patient.treatment_start_time
				+ timedelta(minutes=self.treatment_duration_minutes)
				<= self.current_time
			):
				self.treatment.complete_treatment(patient.patient_id)
				patient.exit_time = self.current_time

	def _refresh_waiting_patients(self) -> None:
		if self.current_time is None:
			return
		current_time = self.current_time
		for patient in self.queue.get_waiting_patients():
			apply_aging(patient, current_time)
			self.queue.update_patient(patient)

	def _admit_arrived_patients(self) -> None:
		if self.current_time is None:
			return
		current_time = self.current_time
		for patient in sorted(
			self._patients.values(),
			key=lambda item: (item.arrival_time, item.internal_record_id or item.patient_id),
		):
			if (
				patient.arrival_time <= current_time
				and patient.status is PatientStatus.WAITING
				and patient.patient_id not in self._queued_ids
			):
				self._assign_public_id(patient)
				self.queue.add_patient(patient)
				self._queued_ids.add(patient.patient_id)

	def _process_events_until(self, target_time: datetime) -> None:
		if self.current_time is None:
			return
		while self.current_time < target_time:
			next_time = target_time
			future_arrivals = [
				patient.arrival_time
				for patient in self._patients.values()
				if patient.status is PatientStatus.WAITING
				and patient.patient_id not in self._queued_ids
				and self.current_time < patient.arrival_time <= target_time
			]
			if future_arrivals:
				next_time = min(next_time, min(future_arrivals))
			completion_times = [
				patient.treatment_start_time
				+ timedelta(minutes=self.treatment_duration_minutes)
				for patient in self.treatment.get_in_treatment_patients()
				if patient.treatment_start_time is not None
				and self.current_time < patient.treatment_start_time
				+ timedelta(minutes=self.treatment_duration_minutes)
				<= target_time
			]
			if completion_times:
				next_time = min(next_time, min(completion_times))
			self.current_time = next_time
			self._complete_due_treatments()
			self._refresh_waiting_patients()
			self._admit_arrived_patients()
			self._fill_treatment_slots()

	def _fill_treatment_slots(self) -> None:
		while not self.treatment.is_full():
			patient = self.call_next()
			if patient is None:
				return