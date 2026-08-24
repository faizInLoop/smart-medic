"""Waiting-queue management for Smart Medic."""

import heapq
import re
from datetime import datetime

from .patient import Patient, PatientStatus


_LEVEL_RANKS = {"RED": 0, "YELLOW": 1, "GREEN": 2}
PriorityKey = tuple[int, int, datetime, int, str]


class PriorityQueueManager:
	"""Manage waiting patients in deterministic clinical priority order."""

	def __init__(self) -> None:
		self._heap: list[PriorityKey] = []
		self._waiting: dict[str, Patient] = {}

	@staticmethod
	def _arrival_sequence(patient_id: str) -> int:
		if not isinstance(patient_id, str) or re.fullmatch(r"\d{4}-\d{3}", patient_id) is None:
			raise ValueError(
				"patient_id must follow the DDMM-NNN format"
			)
		try:
			prefix, sequence = patient_id.rsplit("-", 1)
			if len(prefix) != 4 or len(sequence) != 3:
				raise ValueError
			return int(sequence)
		except (AttributeError, ValueError):
			raise ValueError(
				"patient_id must follow the DDMM-NNN format"
			) from None

	@classmethod
	def _priority_key(cls, patient: Patient) -> PriorityKey:
		if patient.triage_level not in _LEVEL_RANKS:
			raise ValueError("patient must have a RED, YELLOW, or GREEN triage level")
		if patient.queue_priority is None:
			raise ValueError("patient must have a queue priority")
		return (
			_LEVEL_RANKS[patient.triage_level],
			-patient.queue_priority,
			patient.arrival_time,
			cls._arrival_sequence(patient.patient_id),
			patient.patient_id,
		)

	def add_patient(self, patient: Patient) -> None:
		"""Add a patient to the waiting queue."""
		if patient.patient_id in self._waiting:
			raise ValueError(f"patient {patient.patient_id!r} is already waiting")
		patient.status = PatientStatus.WAITING
		priority_key = self._priority_key(patient)
		self._waiting[patient.patient_id] = patient
		heapq.heappush(self._heap, priority_key)

	def update_patient(self, patient: Patient) -> None:
		"""Refresh a waiting patient's heap entry after a priority change."""
		queued_patient = self._waiting.get(patient.patient_id)
		if queued_patient is None:
			raise ValueError(
				f"patient {patient.patient_id!r} is not in the waiting queue"
			)
		if queued_patient is not patient:
			raise ValueError(
				f"patient {patient.patient_id!r} is not the queued patient object"
			)
		if patient.status is not PatientStatus.WAITING:
			raise ValueError(
				"only patients with WAITING status can be updated"
			)

		updated_key = self._priority_key(patient)
		self._heap = [
			priority_key
			for priority_key in self._heap
			if priority_key[-1] != patient.patient_id
		]
		heapq.heapify(self._heap)
		heapq.heappush(self._heap, updated_key)

	def peek_next(self) -> Patient | None:
		"""Return the highest-priority waiting patient without removing it."""
		if not self._heap:
			return None
		return self._waiting[self._heap[0][-1]]

	def pop_next(self) -> Patient | None:
		"""Remove and return the next patient, marking them in treatment."""
		if not self._heap:
			return None
		priority_key = heapq.heappop(self._heap)
		patient = self._waiting.pop(priority_key[-1])
		patient.status = PatientStatus.IN_TREATMENT
		return patient

	def remove_patient(self, patient_id: str) -> bool:
		"""Remove a waiting patient by ID without changing their status."""
		if patient_id not in self._waiting:
			return False
		self._waiting.pop(patient_id)
		self._heap = [
			priority_key
			for priority_key in self._heap
			if priority_key[-1] != patient_id
		]
		heapq.heapify(self._heap)
		return True

	def is_empty(self) -> bool:
		"""Return whether the waiting queue is empty."""
		return not self._heap

	def __len__(self) -> int:
		return len(self._heap)

	def get_waiting_patients(self) -> list[Patient]:
		"""Return waiting patients in priority order without mutation."""
		return [
			self._waiting[priority_key[-1]]
			for priority_key in sorted(self._heap)
		]