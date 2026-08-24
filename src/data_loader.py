"""Load and initialize Smart Medic patients from CSV data."""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .patient import Patient, PatientStatus
from .scoring import calculate_score
from .triage import classify_triage
from .validation import (
	validate_age,
	validate_arrival_time,
	validate_bleeding,
	validate_consciousness,
	validate_heart_rate,
	validate_name,
	validate_patient_id,
	validate_pain_level,
	validate_respiratory_rate,
	validate_spo2,
	validate_systolic_bp,
)


_EXPECTED_COLUMNS = (
	"Patient_Name",
	"Age",
	"SpO2",
	"Heart_Rate",
	"Respiratory_Rate",
	"Systolic_BP",
	"Consciousness",
	"Bleeding",
	"Pain_Level",
	"Arrival_Time",
)
_ARRIVAL_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M")


def load_patients_from_csv(
	path: str | Path,
	current_time: datetime | None = None,
	assign_future_ids: bool = True,
) -> list[Patient]:
	"""Load, validate, score, and classify patients from a Smart Medic CSV."""
	patients: list[Patient] = []
	sequence_by_date: defaultdict[object, int] = defaultdict(int)
	used_ids: set[str] = set()

	with Path(path).open("r", newline="", encoding="utf-8") as csv_file:
		reader = csv.DictReader(csv_file)
		missing_columns = [
			column for column in _EXPECTED_COLUMNS if column not in (reader.fieldnames or [])
		]
		if missing_columns:
			raise ValueError(
				"CSV is missing required columns: " + ", ".join(missing_columns)
			)

		rows = list(enumerate(reader, start=2))
		parsed_rows: list[tuple[int, str, int, int, int, int, int, str, str, int, datetime]] = []
		for row_number, row in rows:
			patient_name = (row.get("Patient_Name") or "<unknown patient>").strip()
			try:
				name = validate_name(row.get("Patient_Name"))
				age = validate_age(int(row["Age"]))
				spo2 = validate_spo2(int(row["SpO2"]))
				heart_rate = validate_heart_rate(int(row["Heart_Rate"]))
				respiratory_rate = validate_respiratory_rate(
					int(row["Respiratory_Rate"])
				)
				systolic_bp = validate_systolic_bp(int(row["Systolic_BP"]))
				consciousness = validate_consciousness(row["Consciousness"])
				bleeding = validate_bleeding(row["Bleeding"])
				pain_level = validate_pain_level(int(row["Pain_Level"]))
				arrival_time = validate_arrival_time(_parse_arrival_time(row["Arrival_Time"]))
				parsed_rows.append(
					(row_number, name, age, spo2, heart_rate, respiratory_rate,
					 systolic_bp, consciousness, bleeding, pain_level, arrival_time)
				)
			except (KeyError, TypeError, ValueError) as error:
				raise ValueError(
					f"CSV row {row_number} for {patient_name!r} is invalid: {error}"
				) from error

		effective_time = current_time
		if not assign_future_ids and effective_time is None and parsed_rows:
			effective_time = min(row[-1] for row in parsed_rows)
		for (
			row_number, name, age, spo2, heart_rate, respiratory_rate,
			systolic_bp, consciousness, bleeding, pain_level, arrival_time,
		) in parsed_rows:
			is_arrived = assign_future_ids or arrival_time <= effective_time
			if is_arrived:
				arrival_date = arrival_time.date()
				sequence_by_date[arrival_date] += 1
				patient_id = f"{arrival_time:%d%m}-{sequence_by_date[arrival_date]:03d}"
				validate_patient_id(patient_id)
				if patient_id in used_ids:
					raise ValueError(f"generated duplicate patient ID {patient_id}")
				used_ids.add(patient_id)
			else:
				patient_id = f"scheduled-{row_number:04d}"

			patient = Patient(
				patient_id=patient_id,
				name=name,
				age=age,
				spo2=spo2,
				heart_rate=heart_rate,
				respiratory_rate=respiratory_rate,
				systolic_bp=systolic_bp,
				consciousness=consciousness,
				bleeding=bleeding,
				pain_level=pain_level,
				arrival_time=arrival_time,
				status=PatientStatus.WAITING,
				internal_record_id=f"csv-row-{row_number:04d}",
			)
			clinical_score = calculate_score(patient)
			triage_result = classify_triage(patient, clinical_score=clinical_score)
			patient.clinical_score = clinical_score
			patient.red_flag = triage_result.red_flag
			patient.triage_level = triage_result.triage_level
			patient.red_flag_reason = triage_result.reason
			patient.aging_adjustment = 0
			patient.queue_priority = clinical_score
			patients.append(patient)

	return patients


def _parse_arrival_time(value: str) -> datetime:
	"""Parse the supported synthetic and demo CSV timestamp formats."""
	for time_format in _ARRIVAL_TIME_FORMATS:
		try:
			return datetime.strptime(value, time_format)
		except ValueError:
			continue
	raise ValueError("arrival time must use YYYY-MM-DD HH:MM:SS or DD-MM-YYYY HH:MM")