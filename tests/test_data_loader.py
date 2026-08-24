from datetime import datetime

import pytest

from src.data_loader import load_patients_from_csv
from src.patient import PatientStatus


HEADER = "Patient_Name,Age,SpO2,Heart_Rate,Respiratory_Rate,Systolic_BP,Consciousness,Bleeding,Pain_Level,Arrival_Time\n"


def test_loads_typed_patients_and_resets_ids_by_date(tmp_path):
	path = tmp_path / "patients.csv"
	path.write_text(
		HEADER
		+ "First,40,98,80,16,120,Normal,,0,2026-08-25 08:00:00\n"
		+ "Second,75,94,110,21,140,Moderate,Mild,5,2026-08-25 08:10:00\n"
		+ "Third,65,95,60,12,100,Normal,None,2,2026-08-26 08:00:00\n",
		encoding="utf-8",
	)
	patients = load_patients_from_csv(path)
	assert len(patients) == 3
	assert [patient.patient_id for patient in patients] == ["2508-001", "2508-002", "2608-001"]
	assert patients[0].bleeding == "None"
	assert patients[0].arrival_time == datetime(2026, 8, 25, 8)
	assert all(patient.status is PatientStatus.WAITING for patient in patients)
	assert all(patient.queue_priority == patient.clinical_score for patient in patients)
	assert patients[0].red_flag_reason is None
	assert all(
		patient.red_flag_reason is not None
		for patient in patients
		if patient.red_flag
	)


def test_invalid_row_has_context(tmp_path):
	path = tmp_path / "invalid.csv"
	path.write_text(HEADER + "Bad Patient,17,98,80,16,120,Normal,None,0,2026-08-25 08:00:00\n", encoding="utf-8")
	with pytest.raises(ValueError, match=r"CSV row 2.*Bad Patient"):
		load_patients_from_csv(path)


def test_demo_timestamp_format_loads():
	patients = load_patients_from_csv("data/smart_medic_demo_15.csv")
	assert len(patients) == 15
	assert patients[0].arrival_time == datetime(2026, 8, 27, 8)
	assert patients[0].patient_id == "2708-001"
