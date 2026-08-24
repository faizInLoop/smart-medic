"""Streamlit dashboard for the Smart Medic prototype."""

from datetime import datetime, timedelta
from html import escape
from pathlib import Path

import streamlit as st

from src.patient import Patient, PatientStatus
from src.scoring import calculate_score
from src.simulation import SmartMedicSimulation
from src.triage import classify_triage
from src.validation import (
    validate_age,
    validate_arrival_time,
    validate_bleeding,
    validate_consciousness,
    validate_heart_rate,
    validate_name,
    validate_pain_level,
    validate_respiratory_rate,
    validate_spo2,
    validate_systolic_bp,
)


DATA_PATH = Path(__file__).parent / "data" / "smart_medic_demo_15.csv"
LEVEL_COLORS = {"RED": "#b42318", "YELLOW": "#b54708", "GREEN": "#087443"}


def initialize_simulation() -> None:
    if "simulation" not in st.session_state:
        simulation = SmartMedicSimulation(
            capacity=1,
            treatment_duration_minutes=40,
            automatic_treatment=True,
        )
        simulation.load_patients(DATA_PATH)
        st.session_state.simulation = simulation
        st.session_state.last_reassessment = None
        st.session_state.last_called = None
        st.session_state.last_registered = None


def get_simulation() -> SmartMedicSimulation:
    initialize_simulation()
    return st.session_state.simulation


def patient_counts(simulation: SmartMedicSimulation) -> dict[PatientStatus, int]:
    counts = {
        status: sum(patient.status is status for patient in simulation._patients.values())
        for status in PatientStatus
    }
    counts[PatientStatus.WAITING] = len(simulation.get_waiting_patients())
    return counts


def render_queue(patients: list[Patient], current_time: datetime) -> None:
    if not patients:
        st.info("No patients are currently waiting.")
        return
    rows = []
    for position, patient in enumerate(patients, start=1):
        wait_minutes = max(0, int((current_time - patient.arrival_time).total_seconds() // 60))
        triage_level = patient.triage_level
        if triage_level is None:
            triage_level = "UNKNOWN"
        rows.append(
            "<tr>"
            f"<td>{position}</td><td>{escape(patient.patient_id)}</td>"
            f"<td>{escape(patient.name)}</td><td>{patient.arrival_time:%Y-%m-%d %H:%M}</td>"
            f"<td>{wait_minutes} min</td><td>{patient.clinical_score}</td>"
            f"<td>{patient.queue_priority}</td>"
            f"<td><span class='level level-{triage_level.lower()}'>{triage_level}</span></td>"
            f"<td>{'Yes' if patient.red_flag else 'No'}</td></tr>"
        )
    st.markdown(
        "<div class='table-wrap'><table><thead><tr>"
        "<th>Position</th><th>Patient ID</th><th>Name</th><th>Arrival Time</th>"
        "<th>Wait Time</th><th>Clinical Score</th><th>Queue Priority</th>"
        "<th>Triage Level</th><th>Red Flag</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def register_patient(simulation: SmartMedicSimulation, values: dict[str, object]) -> Patient:
    name = validate_name(values["name"])
    age = validate_age(values["age"])
    current_time = simulation.current_time
    if current_time is None:
        raise ValueError("simulation time is not initialized")
    arrival_time = validate_arrival_time(values["arrival_time"])
    if arrival_time > current_time:
        raise ValueError("arrival time cannot be later than the current simulation time")
    date_prefix = arrival_time.strftime("%d%m")
    used_sequences = [
        int(patient_id[-3:])
        for patient in simulation._patients.values()
        for patient_id in [patient.patient_id]
        if patient_id.startswith(f"{date_prefix}-") and patient_id[-3:].isdigit()
    ]
    sequence = max(used_sequences, default=0) + 1
    if sequence > 999:
        raise ValueError(
            f"cannot register more than 999 patients for date {date_prefix}"
        )
    patient_id = f"{date_prefix}-{sequence:03d}"
    patient = Patient(
        patient_id=patient_id,
        name=name,
        age=age,
        spo2=validate_spo2(values["spo2"]),
        heart_rate=validate_heart_rate(values["heart_rate"]),
        respiratory_rate=validate_respiratory_rate(values["respiratory_rate"]),
        systolic_bp=validate_systolic_bp(values["systolic_bp"]),
        consciousness=validate_consciousness(values["consciousness"]),
        bleeding=validate_bleeding(values["bleeding"]),
        pain_level=validate_pain_level(values["pain_level"]),
        arrival_time=arrival_time,
        status=PatientStatus.WAITING,
        internal_record_id=f"manual-{date_prefix}-{sequence:03d}",
    )
    patient.clinical_score = calculate_score(patient)
    triage_result = classify_triage(patient, clinical_score=patient.clinical_score)
    patient.red_flag = triage_result.red_flag
    patient.triage_level = triage_result.triage_level
    patient.red_flag_reason = triage_result.reason
    patient.queue_priority = patient.clinical_score
    simulation.queue.add_patient(patient)
    simulation._next_sequence_by_date[arrival_time.date()] = sequence
    simulation._patients[patient.internal_record_id or patient.patient_id] = patient
    simulation._queued_ids.add(patient.patient_id)

    # In automatic-treatment demo mode, immediately use a free treatment slot.
    if simulation.automatic_treatment and not simulation.treatment.is_full():
        simulation._fill_treatment_slots()

    return patient


def render_summary(simulation: SmartMedicSimulation) -> None:
    counts = patient_counts(simulation)
    cards = [
        ("Registered", len(simulation._patients)),
        ("Waiting", counts[PatientStatus.WAITING]),
        ("In Treatment", counts[PatientStatus.IN_TREATMENT]),
        ("Completed", counts[PatientStatus.COMPLETED]),
        ("Referred", counts[PatientStatus.REFERRED]),
        ("RED", sum(p.triage_level == "RED" for p in simulation._patients.values())),
        ("YELLOW", sum(p.triage_level == "YELLOW" for p in simulation._patients.values())),
        ("GREEN", sum(p.triage_level == "GREEN" for p in simulation._patients.values())),
    ]
    columns = st.columns(8)
    for column, (label, value) in zip(columns, cards):
        column.metric(label, value)

    metrics = simulation.get_performance_metrics()
    performance_columns = st.columns(3)
    performance_columns[0].metric(
        "Average Waiting Time", f"{metrics['average_waiting_minutes']:.1f} min"
    )
    performance_columns[1].metric(
        "Average Turnaround Time", f"{metrics['average_turnaround_minutes']:.1f} min"
    )
    performance_columns[2].metric("Patients Served", metrics["patients_served"])


def render_reassessment(simulation: SmartMedicSimulation) -> None:
    waiting = simulation.get_waiting_patients()
    if not waiting:
        st.info("There are no waiting patients to reassess.")
        return
    options = {f"{patient.patient_id} · {patient.name}": patient for patient in waiting}
    selected_label = st.selectbox("Patient", list(options), key="reassessment_patient")
    patient = options[selected_label]
    current_time = simulation.current_time
    if current_time is None:
        st.error("Simulation time is not initialized.")
        return
    wait_minutes = max(0, int((current_time - patient.arrival_time).total_seconds() // 60))
    st.caption(
        f"Current score: {patient.clinical_score} · Level: {patient.triage_level} · "
        f"Red flag: {'Yes' if patient.red_flag else 'No'} · Wait: {wait_minutes} min"
    )
    with st.form("reassessment_form"):
        columns = st.columns(4)
        spo2 = columns[0].number_input("SpO2", 0, 100, patient.spo2)
        heart_rate = columns[1].number_input("Heart Rate", 20, 250, patient.heart_rate)
        respiratory_rate = columns[2].number_input("Respiratory Rate", 4, 60, patient.respiratory_rate)
        systolic_bp = columns[3].number_input("Systolic BP", 50, 250, patient.systolic_bp)
        consciousness = st.selectbox("Consciousness", ["Normal", "Moderate", "Severe", "Unresponsive"], index=["Normal", "Moderate", "Severe", "Unresponsive"].index(patient.consciousness))
        bleeding = st.selectbox("Bleeding", ["None", "Mild", "Moderate", "Severe"], index=["None", "Mild", "Moderate", "Severe"].index(patient.bleeding))
        pain = st.slider("Pain Level", 0, 10, patient.pain_level)
        submitted = st.form_submit_button("Update assessment", type="primary")
    if submitted:
        try:
            st.session_state.last_reassessment = simulation.reassess_patient(
                patient.patient_id, spo2, heart_rate, respiratory_rate, systolic_bp,
                consciousness, bleeding, pain,
            )
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    result = st.session_state.get("last_reassessment")
    if result and result.patient_id == patient.patient_id:
        st.success(
            f"Score {result.previous_score} → {result.new_score}; "
            f"level {result.previous_triage_level} → {result.new_triage_level}. "
            f"Changed: {', '.join(result.changed_fields) or 'none'}."
        )
        if result.red_flag_reason:
            st.warning(f"Red flag: {result.red_flag_reason}")


def render_patient_outcomes(simulation: SmartMedicSimulation) -> None:
    """Display completed and referred patients, newest outcome first."""
    outcomes = sorted(
        (
            patient
            for patient in simulation._patients.values()
            if patient.status in {PatientStatus.COMPLETED, PatientStatus.REFERRED}
            and patient.treatment_start_time is not None
            and patient.exit_time is not None
        ),
        key=lambda patient: patient.exit_time or datetime.min,
        reverse=True,
    )
    st.header("Patient Outcomes")
    if not outcomes:
        st.caption("No patient outcomes yet.")
        return
    rows = []
    for patient in outcomes:
        treatment_start_time = patient.treatment_start_time
        exit_time = patient.exit_time
        if treatment_start_time is None or exit_time is None:
            continue
        waiting_minutes = int(
            (treatment_start_time - patient.arrival_time).total_seconds() // 60
        )
        turnaround_minutes = int(
            (exit_time - patient.arrival_time).total_seconds() // 60
        )
        rows.append(
            "<tr>"
            f"<td>{escape(patient.patient_id)}</td><td>{escape(patient.name)}</td>"
            f"<td>{patient.triage_level}</td><td>{patient.clinical_score}</td>"
            f"<td>{patient.arrival_time:%Y-%m-%d %H:%M}</td>"
            f"<td>{treatment_start_time:%Y-%m-%d %H:%M}</td>"
            f"<td>{exit_time:%Y-%m-%d %H:%M}</td>"
            f"<td>{waiting_minutes} min</td><td>{turnaround_minutes} min</td>"
            f"<td>{patient.status.name}</td>"
            f"<td>{escape(patient.red_flag_reason or 'None')}</td></tr>"
        )
    st.markdown(
        "<div class='table-wrap'><table><thead><tr>"
        "<th>Patient ID</th><th>Name</th><th>Triage Level</th><th>Clinical Score</th>"
        "<th>Arrival Time</th><th>Treatment Start Time</th><th>Exit Time</th>"
        "<th>Waiting Time</th><th>Turnaround Time</th><th>Outcome</th><th>Red Flag Reason</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Smart Medic", page_icon="+", layout="wide")
    st.markdown("""
    <style>
    .block-container { max-width: 1400px; padding-top: 2rem; }
    .table-wrap { overflow-x: auto; border: 1px solid #d9dee7; border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
    th { background: #f4f6f8; color: #344054; font-weight: 600; text-align: left; }
    th, td { padding: 0.65rem 0.7rem; border-bottom: 1px solid #eaecf0; white-space: nowrap; }
    tr:last-child td { border-bottom: 0; }
    .level { border-radius: 999px; color: white; font-weight: 700; padding: 0.2rem 0.5rem; font-size: 0.75rem; }
    .level-red { background: #b42318; } .level-yellow { background: #b54708; } .level-green { background: #087443; }
    </style>
    """, unsafe_allow_html=True)
    simulation = get_simulation()

    with st.sidebar:
        st.title("Smart Medic")
        st.caption("Clinic operations")
        st.divider()
        st.write("Simulation time")
        st.write(simulation.current_time.strftime("%Y-%m-%d %H:%M") if simulation.current_time else "Not initialized")
        st.write(f"Treatment capacity: {simulation.treatment.capacity}")
        st.write(f"Available slots: {simulation.treatment.available_slots()}")
        st.divider()
        st.subheader("Advance time")
        for minutes in (10, 20, 30, 40, 60):
            if st.button(f"+{minutes} minutes", use_container_width=True):
                simulation.advance_time(minutes)
                st.rerun()
        if st.button("Reset Simulation", use_container_width=True):
            for key in ("simulation", "last_reassessment", "last_called", "last_registered"):
                st.session_state.pop(key, None)
            st.rerun()

    current_time = simulation.current_time
    if current_time is None:
        st.error("Simulation time is not initialized.")
        return

    st.title("Smart Medic")
    st.caption("Rule-based emergency triage and waiting-queue prioritization")
    st.info("Smart Medic is a rule-based triage prioritization prototype for adult patients. It does not diagnose patients or replace clinical judgment.")
    render_summary(simulation)

    st.header("Waiting Queue")
    render_queue(simulation.get_waiting_patients(), current_time)

    left, right = st.columns(2)
    with left:
        st.header("Register Patient")
        with st.form("register_form"):
            name = st.text_input("Name")
            age = st.number_input("Age", min_value=0, max_value=150, value=40)
            col1, col2 = st.columns(2)
            spo2 = col1.number_input("SpO2", 0, 200, 98)
            heart_rate = col2.number_input("Heart Rate", 0, 1000, 80)
            respiratory_rate = col1.number_input("Respiratory Rate", 0, 200, 16)
            systolic_bp = col2.number_input("Systolic BP", 0, 400, 120)
            consciousness = st.selectbox("Consciousness", ["Normal", "Moderate", "Severe", "Unresponsive"], key="register_consciousness")
            bleeding = st.selectbox("Bleeding", ["None", "Mild", "Moderate", "Severe"], key="register_bleeding")
            pain = st.slider("Pain Level", 0, 10, 0, key="register_pain")
            registration_time = simulation.current_time
            default_date = registration_time.date() if registration_time else datetime.now().date()
            default_time = registration_time.time().replace(second=0, microsecond=0) if registration_time else datetime.now().time().replace(second=0, microsecond=0)
            arrival_date = st.date_input("Arrival Date", value=default_date)
            arrival_time_value = st.time_input("Arrival Time", value=default_time)
            submitted = st.form_submit_button("Register patient", type="primary")
        if submitted:
            try:
                patient = register_patient(simulation, {"name": name, "age": age, "spo2": spo2, "heart_rate": heart_rate, "respiratory_rate": respiratory_rate, "systolic_bp": systolic_bp, "consciousness": consciousness, "bleeding": bleeding, "pain_level": pain, "arrival_time": datetime.combine(arrival_date, arrival_time_value)})
                st.session_state.last_registered = patient
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    with right:
        st.header("Reassessment")
        render_reassessment(simulation)

    st.header("Treatment")
    st.info("Treatment slots are automatically filled from the highest-priority waiting queue when a slot becomes available.")
    active = simulation.get_in_treatment_patients()
    slot_columns = st.columns(simulation.treatment.capacity)
    for index in range(simulation.treatment.capacity):
        with slot_columns[index]:
            patient = active[index] if index < len(active) else None
            if patient is None:
                st.write(f"Slot {index + 1}: Available")
            else:
                start_time = patient.treatment_start_time
                if start_time is None:
                    st.write(f"Slot {index + 1}: {patient.patient_id} · timing unavailable")
                    continue
                expected_completion = start_time + timedelta(minutes=simulation.treatment_duration_minutes)
                remaining = max(0, int((expected_completion - current_time).total_seconds() // 60))
                st.write(f"Slot {index + 1}: {patient.patient_id} · {remaining} min remaining")
    st.caption("Patients in treatment are not interrupted by newly higher-priority arrivals.")
    if active:
        for patient in active:
            columns = st.columns([3, 2, 1, 1])
            columns[0].write(f"**{patient.patient_id}** · {patient.name}")
            start_time = patient.treatment_start_time
            if start_time is None:
                columns[1].write("Treatment timing unavailable")
                continue
            expected_completion = start_time + timedelta(minutes=simulation.treatment_duration_minutes)
            columns[1].write(
                f"{patient.triage_level} · score {patient.clinical_score} · "
                f"started {start_time:%H:%M} · "
                f"expected {expected_completion:%H:%M}"
            )
            columns[2].write("Auto-completes")
            if columns[3].button("Refer", key=f"refer_{patient.patient_id}"):
                simulation.refer_patient(patient.patient_id)
                st.rerun()
    else:
        st.caption("No patients currently in treatment.")

    render_patient_outcomes(simulation)

    st.header("Patient History")
    lookup = st.text_input("Patient ID", placeholder="e.g. 2508-001")
    if lookup:
        patient = next(
            (
                patient for patient in simulation._patients.values()
                if patient.patient_id == lookup.strip()
            ),
            None,
        )
        if patient is None:
            st.warning("Patient ID not found.")
        else:
            st.json({
                "patient_id": patient.patient_id,
                "name": patient.name,
                "age": patient.age,
                "arrival_time": patient.arrival_time.isoformat(sep=" "),
                "status": patient.status.name,
                "clinical_score": patient.clinical_score,
                "triage_level": patient.triage_level,
                "red_flag": patient.red_flag,
                "red_flag_reason": patient.red_flag_reason,
                "queue_priority": patient.queue_priority,
            })


if __name__ == "__main__":
    main()