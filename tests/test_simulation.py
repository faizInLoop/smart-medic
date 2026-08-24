from datetime import datetime

from src.patient import PatientStatus
import pytest
from src.simulation import SmartMedicSimulation


HEADER = "Patient_Name,Age,SpO2,Heart_Rate,Respiratory_Rate,Systolic_BP,Consciousness,Bleeding,Pain_Level,Arrival_Time\n"


def test_simulation_load_advance_reassess_call_and_complete(tmp_path):
	path = tmp_path / "patients.csv"
	path.write_text(
		HEADER
		+ "Early,40,98,80,16,120,Normal,None,0,2026-08-25 08:00:00\n"
		+ "Future,40,98,80,16,120,Normal,None,0,2026-08-25 09:00:00\n"
		+ "Red,40,87,80,16,120,Normal,None,0,2026-08-25 08:30:00\n",
		encoding="utf-8",
	)
	simulation = SmartMedicSimulation(capacity=1)
	loaded = simulation.load_patients(path)
	assert len(loaded) == 3
	assert [patient.name for patient in simulation.get_waiting_patients()] == ["Early"]

	simulation.advance_time(30)
	assert {patient.name for patient in simulation.get_waiting_patients()} == {"Early", "Red"}
	simulation.advance_time(30)
	assert {patient.name for patient in simulation.get_waiting_patients()} == {"Early", "Future", "Red"}

	early = next(patient for patient in loaded if patient.name == "Early")
	simulation.reassess_patient(early.patient_id, 87, 151, 31, 79, "Unresponsive", "Severe", 10)
	assert early.triage_level == "RED"
	assert simulation.get_waiting_patients()[0] is early

	called = simulation.call_next()
	assert called is early
	assert called.status is PatientStatus.IN_TREATMENT
	assert called not in simulation.get_waiting_patients()
	assert called in simulation.get_in_treatment_patients()
	assert simulation.treatment.available_slots() == 0

	completed = simulation.complete_treatment(called.patient_id)
	assert completed.status is PatientStatus.COMPLETED
	assert simulation.treatment.available_slots() == 1


def test_future_reassessment_fails_without_mutating_patient(tmp_path):
	path = tmp_path / "patients.csv"
	path.write_text(
		HEADER
		+ "Early,40,98,80,16,120,Normal,None,0,2026-08-25 08:00:00\n"
		+ "Future,40,98,80,16,120,Normal,None,0,2026-08-25 09:00:00\n",
		encoding="utf-8",
	)
	simulation = SmartMedicSimulation()
	patients = simulation.load_patients(path)
	future = next(patient for patient in patients if patient.name == "Future")
	original = (
		future.spo2, future.heart_rate, future.respiratory_rate,
		future.systolic_bp, future.consciousness, future.bleeding,
		future.pain_level, future.clinical_score, future.triage_level,
		future.red_flag, future.queue_priority,
	)
	with pytest.raises(ValueError, match="waiting queue"):
		simulation.reassess_patient(
			future.patient_id, 87, 151, 31, 79, "Unresponsive", "Severe", 10
		)
	assert original == (
		future.spo2, future.heart_rate, future.respiratory_rate,
		future.systolic_bp, future.consciousness, future.bleeding,
		future.pain_level, future.clinical_score, future.triage_level,
		future.red_flag, future.queue_priority,
	)


def test_registration_rejects_sequence_1000_without_mutation(tmp_path):
	from app import register_patient

	path = tmp_path / "patients.csv"
	rows = "".join(
		f"Patient {index},40,98,80,16,120,Normal,None,0,2026-08-25 08:00:00\n"
		for index in range(999)
	)
	path.write_text(HEADER + rows, encoding="utf-8")
	simulation = SmartMedicSimulation()
	simulation.load_patients(path)
	values = {
		"name": "Overflow", "age": 40, "spo2": 98, "heart_rate": 80,
		"respiratory_rate": 16, "systolic_bp": 120, "consciousness": "Normal",
		"bleeding": "None", "pain_level": 0, "arrival_time": simulation.current_time,
	}
	registry_before = dict(simulation._patients)
	queue_before = list(simulation.get_waiting_patients())
	sequence_before = dict(simulation._next_sequence_by_date)
	with pytest.raises(ValueError, match="999"):
		register_patient(simulation, values)
	assert simulation._patients == registry_before
	assert simulation.get_waiting_patients() == queue_before
	assert dict(simulation._next_sequence_by_date) == sequence_before


def test_automatic_treatment_completes_and_promotes_waiting_patients(tmp_path):
	path = tmp_path / "patients.csv"
	path.write_text(
		HEADER
		+ "First,40,98,80,16,120,Normal,None,0,2026-08-25 08:00:00\n"
		+ "Second,40,98,80,16,120,Normal,None,0,2026-08-25 08:05:00\n"
		+ "Third,40,87,80,16,120,Normal,None,0,2026-08-25 08:10:00\n",
		encoding="utf-8",
	)
	simulation = SmartMedicSimulation(
		capacity=2, automatic_treatment=True, treatment_duration_minutes=20
	)
	patients = simulation.load_patients(path)
	assert [patient.name for patient in simulation.get_in_treatment_patients()] == ["First"]
	assert patients[0].treatment_start_time == datetime(2026, 8, 25, 8)
	simulation.advance_time(10)
	assert [patient.name for patient in simulation.get_in_treatment_patients()] == ["First", "Second"]
	simulation.advance_time(10)
	assert patients[0].status is PatientStatus.COMPLETED
	assert patients[0].exit_time == datetime(2026, 8, 25, 8, 20)
	assert [patient.name for patient in simulation.get_in_treatment_patients()] == ["Second", "Third"]
	assert patients[1].treatment_start_time == datetime(2026, 8, 25, 8, 5)
	assert patients[2].treatment_start_time == datetime(2026, 8, 25, 8, 20)


def test_automatic_treatment_metrics_include_completion_and_referral(tmp_path):
	path = tmp_path / "patients.csv"
	path.write_text(
		HEADER
		+ "First,40,98,80,16,120,Normal,None,0,2026-08-25 08:00:00\n"
		+ "Second,40,98,80,16,120,Normal,None,0,2026-08-25 08:00:00\n",
		encoding="utf-8",
	)
	simulation = SmartMedicSimulation(capacity=2, automatic_treatment=True)
	patients = simulation.load_patients(path)
	simulation.advance_time(20)
	assert all(patient.status is PatientStatus.COMPLETED for patient in patients)
	metrics = simulation.get_performance_metrics()
	assert metrics == {
		"average_waiting_minutes": 0.0,
		"average_turnaround_minutes": 20.0,
		"patients_served": 2,
	}


def test_referral_is_included_in_service_metrics(tmp_path):
	path = tmp_path / "patients.csv"
	path.write_text(
		HEADER
		+ "First,40,98,80,16,120,Normal,None,0,2026-08-25 08:00:00\n",
		encoding="utf-8",
	)
	simulation = SmartMedicSimulation(capacity=2, automatic_treatment=True)
	patient = simulation.load_patients(path)[0]
	simulation.refer_patient(patient.patient_id)
	assert patient.status is PatientStatus.REFERRED
	assert simulation.get_performance_metrics() == {
		"average_waiting_minutes": 0.0,
		"average_turnaround_minutes": 0.0,
		"patients_served": 1,
	}


def test_automatic_registration_immediately_enters_free_treatment_slot():
    from app import register_patient

    simulation = SmartMedicSimulation(
        current_time=datetime(2026, 8, 25, 8, 30),
        capacity=1,
        automatic_treatment=True,
        treatment_duration_minutes=40,
    )

    patient = register_patient(
        simulation,
        {
            "name": "Immediate Treatment",
            "age": 40,
            "spo2": 82,
            "heart_rate": 160,
            "respiratory_rate": 32,
            "systolic_bp": 78,
            "consciousness": "Severe",
            "bleeding": "Severe",
            "pain_level": 10,
            "arrival_time": datetime(2026, 8, 25, 8, 30),
        },
    )

    assert patient.status is PatientStatus.IN_TREATMENT
    assert patient.treatment_start_time == datetime(2026, 8, 25, 8, 30)
    assert simulation.get_waiting_patients() == []
    assert simulation.get_in_treatment_patients() == [patient]


def test_automatic_registration_waits_when_treatment_slot_is_occupied():
    from app import register_patient

    simulation = SmartMedicSimulation(
        current_time=datetime(2026, 8, 25, 8, 0),
        capacity=1,
        automatic_treatment=True,
        treatment_duration_minutes=40,
    )

    first = register_patient(
        simulation,
        {
            "name": "Current Patient",
            "age": 40,
            "spo2": 98,
            "heart_rate": 80,
            "respiratory_rate": 16,
            "systolic_bp": 120,
            "consciousness": "Normal",
            "bleeding": "None",
            "pain_level": 0,
            "arrival_time": datetime(2026, 8, 25, 8, 0),
        },
    )

    second = register_patient(
        simulation,
        {
            "name": "Waiting Red",
            "age": 40,
            "spo2": 82,
            "heart_rate": 160,
            "respiratory_rate": 32,
            "systolic_bp": 78,
            "consciousness": "Severe",
            "bleeding": "Severe",
            "pain_level": 10,
            "arrival_time": datetime(2026, 8, 25, 8, 0),
        },
    )

    assert first.status is PatientStatus.IN_TREATMENT
    assert second.status is PatientStatus.WAITING
    assert second in simulation.get_waiting_patients()
    assert simulation.get_waiting_patients()[0] is second
    assert len(simulation.get_in_treatment_patients()) == 1


def test_arrived_registration_is_immediately_in_waiting_queue():
	from app import register_patient

	simulation = SmartMedicSimulation(current_time=datetime(2026, 8, 25, 8, 30))
	patient = register_patient(
		simulation,
		{
			"name": "Immediate Red",
			"age": 40,
			"spo2": 87,
			"heart_rate": 80,
			"respiratory_rate": 16,
			"systolic_bp": 120,
			"consciousness": "Normal",
			"bleeding": "None",
			"pain_level": 0,
			"arrival_time": datetime(2026, 8, 25, 8, 30),
		},
	)
	assert patient.status is PatientStatus.WAITING
	assert simulation.get_waiting_patients() == [patient]
	assert simulation.get_waiting_patients()[0].triage_level == "RED"


def test_streamlit_registration_refreshes_waiting_queue_immediately():
	from streamlit.testing.v1 import AppTest

	app = AppTest.from_file("app.py").run()
	assert not app.exception
	next(button for button in app.button if button.label == "+30 minutes").click().run()
	assert not app.exception
	waiting_before = next(metric for metric in app.metric if metric.label == "Waiting")
	assert waiting_before.value == "2"

	app.text_input[0].set_value("Immediate Red")
	app.number_input[0].set_value(40)
	app.number_input[1].set_value(87)
	app.number_input[2].set_value(16)
	app.number_input[3].set_value(80)
	app.number_input[4].set_value(120)
	next(button for button in app.button if button.label == "Register patient").click().run()
	assert not app.exception
	waiting_after = next(metric for metric in app.metric if metric.label == "Waiting")
	assert waiting_after.value == "3"
	assert any("Immediate Red" in item.value for item in app.markdown)


def test_streamlit_patient_outcomes_show_only_exited_patients():
	from streamlit.testing.v1 import AppTest

	app = AppTest.from_file("app.py").run()
	assert not app.exception
	assert any("No patient outcomes yet." in item.value for item in app.caption)

	next(button for button in app.button if button.label == "+40 minutes").click().run()
	assert not app.exception
	assert any("Nitin Gupta" in item.value for item in app.markdown)
	assert not any("No patient outcomes yet." in item.value for item in app.caption)

	refer_button = next(button for button in app.button if button.label == "Refer")
	refer_button.click().run()
	assert not app.exception
	outcome_markdown = [item.value for item in app.markdown]
	outcome_table = next(value for value in outcome_markdown if "<th>Outcome</th>" in value)
	assert "COMPLETED" in outcome_table
	assert "REFERRED" in outcome_table
	assert "Red Flag Reason" in outcome_table
	assert "Unresponsive" not in outcome_table
	assert "Priya Pillai" not in outcome_table


def test_streamlit_patient_history_displays_red_flag_reason():
	import json
	from streamlit.testing.v1 import AppTest

	app = AppTest.from_file("app.py").run()
	app.text_input[1].set_value("2708-001")
	app.run()
	assert not app.exception
	history = json.loads(app.json[0].value)
	assert history["red_flag"] is False
	assert history["red_flag_reason"] is None

	for minutes in (60, 60, 20):
		next(button for button in app.button if button.label == f"+{minutes} minutes").click().run()
	app.text_input[1].set_value("2708-007")
	app.run()
	history = app.json[0].value
	history = json.loads(history)
	assert history["red_flag"] is True
	assert history["red_flag_reason"] is not None


def test_large_time_jump_processes_treatment_events_chronologically(tmp_path):
	path = tmp_path / "patients.csv"
	path.write_text(
		HEADER
		+ "A,40,98,80,16,120,Normal,None,0,2026-08-25 08:00:00\n"
		+ "B,40,98,80,16,120,Normal,None,0,2026-08-25 08:14:00\n"
		+ "C,40,87,80,16,120,Normal,None,0,2026-08-25 08:19:00\n",
		encoding="utf-8",
	)
	simulation = SmartMedicSimulation(capacity=1, automatic_treatment=True)
	patients = simulation.load_patients(path)
	simulation.advance_time(120)
	assert patients[0].treatment_start_time == datetime(2026, 8, 25, 8)
	assert patients[0].exit_time == datetime(2026, 8, 25, 8, 20)
	assert patients[2].treatment_start_time == datetime(2026, 8, 25, 8, 20)
	assert patients[2].exit_time == datetime(2026, 8, 25, 8, 40)
	assert patients[1].treatment_start_time == datetime(2026, 8, 25, 8, 40)
	assert patients[1].exit_time == datetime(2026, 8, 25, 9)
	assert all(patient.status is PatientStatus.COMPLETED for patient in patients)
	metrics = simulation.get_performance_metrics()
	assert metrics["average_waiting_minutes"] == 9
	assert metrics["average_turnaround_minutes"] == 29
	assert metrics["patients_served"] == 3


def test_demo_one_slot_has_exact_40_minute_treatment_and_no_interruption(tmp_path):
	path = tmp_path / "patients.csv"
	path.write_text(
		HEADER
		+ "A,40,98,80,16,120,Normal,None,0,2026-08-25 08:00:00\n"
		+ "B,40,87,80,16,120,Normal,None,0,2026-08-25 08:10:00\n",
		encoding="utf-8",
	)
	simulation = SmartMedicSimulation(
		capacity=1, automatic_treatment=True, treatment_duration_minutes=40
	)
	patients = simulation.load_patients(path)
	assert patients[0].status is PatientStatus.IN_TREATMENT
	simulation.advance_time(39)
	assert patients[0].status is PatientStatus.IN_TREATMENT
	assert patients[1].status is PatientStatus.WAITING
	simulation.advance_time(1)
	assert patients[0].status is PatientStatus.COMPLETED
	assert patients[0].exit_time == datetime(2026, 8, 25, 8, 40)
	assert patients[1].status is PatientStatus.IN_TREATMENT
	assert patients[1].treatment_start_time == datetime(2026, 8, 25, 8, 40)