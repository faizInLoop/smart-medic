"""Treatment-related components for Smart Medic."""

from numbers import Integral

from .patient import Patient, PatientStatus


class TreatmentManager:
	"""Manage treatment capacity and in-treatment patient transitions."""

	def __init__(self, capacity: int = 3) -> None:
		if isinstance(capacity, bool) or not isinstance(capacity, Integral) or capacity < 1:
			raise ValueError("treatment capacity must be a positive integer")
		self.capacity = capacity
		self._in_treatment: dict[str, Patient] = {}

	def start_treatment(self, patient: Patient) -> None:
		"""Move a waiting patient into an available treatment slot."""
		if patient.status is not PatientStatus.WAITING:
			raise ValueError("only patients with WAITING status can start treatment")
		if self.is_full():
			raise ValueError("no treatment slots are available")
		if patient.patient_id in self._in_treatment:
			raise ValueError(f"patient {patient.patient_id!r} is already in treatment")
		patient.status = PatientStatus.IN_TREATMENT
		self._in_treatment[patient.patient_id] = patient

	def complete_treatment(self, patient_id: str) -> Patient:
		"""Complete treatment and free the patient's treatment slot."""
		patient = self._get_active_patient(patient_id)
		patient.status = PatientStatus.COMPLETED
		return self._in_treatment.pop(patient_id)

	def refer_patient(self, patient_id: str) -> Patient:
		"""Refer a patient and free the patient's treatment slot."""
		patient = self._get_active_patient(patient_id)
		patient.status = PatientStatus.REFERRED
		return self._in_treatment.pop(patient_id)

	def _get_active_patient(self, patient_id: str) -> Patient:
		patient = self._in_treatment.get(patient_id)
		if patient is None or patient.status is not PatientStatus.IN_TREATMENT:
			raise ValueError(f"patient {patient_id!r} is not in treatment")
		return patient

	def available_slots(self) -> int:
		"""Return the number of currently available treatment slots."""
		return self.capacity - len(self._in_treatment)

	def in_treatment_count(self) -> int:
		"""Return the number of currently active treatment patients."""
		return len(self._in_treatment)

	def get_in_treatment_patients(self) -> list[Patient]:
		"""Return active treatment patients in start order."""
		return list(self._in_treatment.values())

	def is_full(self) -> bool:
		"""Return whether all treatment slots are occupied."""
		return self.in_treatment_count() >= self.capacity