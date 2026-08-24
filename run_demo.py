"""Run a concise Smart Medic workflow demonstration."""

from collections import Counter
from pathlib import Path

from src.patient import PatientStatus
from src.simulation import SmartMedicSimulation


DATA_PATH = Path("data") / "smart_medic_synthetic_150.csv"


def print_queue(title: str, patients: list) -> None:
    print(title)
    print("=" * len(title))
    if not patients:
        print("(empty)")
        return
    print("Pos  ID         Name                 Arrival              Score  Priority  Level   Red")
    for position, patient in enumerate(patients[:10], start=1):
        print(
            f"{position:>3}  {patient.patient_id:<10} "
            f"{patient.name:<20} {patient.arrival_time:%Y-%m-%d %H:%M} "
            f"{patient.clinical_score:>5}  {patient.queue_priority:>8}  "
            f"{patient.triage_level:<6}  {str(patient.red_flag):<5}"
        )


def main() -> None:
    simulation = SmartMedicSimulation()
    patients = simulation.load_patients(DATA_PATH)
    levels = Counter(patient.triage_level for patient in patients)

    print("SMART MEDIC DEMO")
    print("================")
    print(f"Patients loaded: {len(patients)}")
    print(f"Current simulation time: {simulation.current_time}")
    print(f"RED patients: {levels['RED']}")
    print(f"YELLOW patients: {levels['YELLOW']}")
    print(f"GREEN patients: {levels['GREEN']}")
    print()

    waiting = simulation.get_waiting_patients()
    print_queue("INITIAL WAITING QUEUE", waiting)
    future_patients = [
        patient for patient in patients
        if patient.arrival_time > simulation.current_time
    ]
    print(f"\nFuture arrivals not yet arrived: {len(future_patients)}")

    before_aging = {
        patient.patient_id: (patient.clinical_score, patient.triage_level, patient.queue_priority)
        for patient in waiting
    }
    simulation.advance_time(40)
    waiting = simulation.get_waiting_patients()
    print("\nAFTER 40 MINUTES")
    print("================")
    print(f"Current simulation time: {simulation.current_time}")
    print_queue("TOP 10 WAITING PATIENTS", waiting)
    aging_changes = [
        patient for patient in waiting
        if patient.patient_id in before_aging
        and patient.queue_priority != before_aging[patient.patient_id][2]
    ]
    print(f"Aging priority changes visible: {len(aging_changes)}")
    for patient in aging_changes[:5]:
        old_score, old_level, old_priority = before_aging[patient.patient_id]
        unchanged = patient.clinical_score == old_score and patient.triage_level == old_level
        print(
            f"  {patient.patient_id}: priority {old_priority} -> {patient.queue_priority}; "
            f"clinical score/triage unchanged: {unchanged}"
        )

    previously_waiting = {patient.patient_id for patient in waiting}
    next_arrival = min(
        (patient for patient in patients if patient.arrival_time > simulation.current_time),
        key=lambda patient: patient.arrival_time,
        default=None,
    )
    if next_arrival is None:
        raise RuntimeError("No future arrival is available for the demonstration")
    minutes_to_arrival = int(
        (next_arrival.arrival_time - simulation.current_time).total_seconds() // 60
    )
    simulation.advance_time(minutes_to_arrival)
    newly_arrived = [
        patient for patient in simulation.get_waiting_patients()
        if patient.patient_id not in previously_waiting
    ]
    print("\nFUTURE ARRIVAL DEMONSTRATION")
    print("============================")
    print(f"Advanced to: {simulation.current_time}")
    for patient in newly_arrived:
        print(f"Newly arrived: {patient.patient_id} - {patient.name}")
    print(f"Updated waiting queue size: {len(simulation.get_waiting_patients())}")
    print_queue("UPDATED TOP 10 QUEUE", simulation.get_waiting_patients())

    reassessed = simulation.get_waiting_patients()[0]
    before_reassessment = simulation.get_waiting_patients()
    old_position = before_reassessment.index(reassessed) + 1
    old_score = reassessed.clinical_score
    old_level = reassessed.triage_level
    print("\nREASSESSMENT")
    print("============")
    print(f"Patient: {reassessed.patient_id}")
    print(f"Name: {reassessed.name}")
    print(f"Clinical score: {old_score}")
    print(f"Triage level: {old_level}")
    print(f"Red flag: {reassessed.red_flag}")
    result = simulation.reassess_patient(
        reassessed.patient_id,
        83,
        151,
        31,
        79,
        "Unresponsive",
        "Severe",
        10,
    )
    after_reassessment = simulation.get_waiting_patients()
    new_position = after_reassessment.index(reassessed) + 1
    print(f"Old score: {result.previous_score}")
    print(f"New score: {result.new_score}")
    print(f"Old triage level: {result.previous_triage_level}")
    print(f"New triage level: {result.new_triage_level}")
    print(f"Red flag: {result.new_red_flag}; reason: {result.red_flag_reason}")
    print(f"Old queue position: {old_position}")
    print(f"New queue position: {new_position}")
    print_queue("UPDATED TOP 10 QUEUE", after_reassessment)

    called = simulation.call_next()
    if called is None:
        raise RuntimeError("No patient was available for treatment")
    print("\nCALLED FOR TREATMENT")
    print("====================")
    print(f"Patient ID: {called.patient_id}")
    print(f"Name: {called.name}")
    print(f"Triage level: {called.triage_level}")
    print(f"Clinical score: {called.clinical_score}")
    print(f"Current status: {called.status.name}")
    print(f"Available treatment slots: {simulation.treatment.available_slots()}")
    completed = simulation.complete_treatment(called.patient_id)
    print(f"Final status: {completed.status.name}")
    print(f"Available treatment slots: {simulation.treatment.available_slots()}")

    referred = simulation.call_next()
    if referred is None:
        raise RuntimeError("No second patient was available for referral")
    simulation.refer_patient(referred.patient_id)
    print("\nREFERRAL")
    print("========")
    print(f"Patient ID: {referred.patient_id}")
    print(f"Status: {referred.status.name}")
    print(f"Available treatment slots: {simulation.treatment.available_slots()}")

    status_counts = Counter(patient.status for patient in patients)
    print("\nDEMO COMPLETED")
    print("==============")
    print(f"Patients loaded: {len(patients)}")
    print(f"Current waiting count: {sum(patient.status is PatientStatus.WAITING for patient in patients)}")
    print(f"In-treatment count: {status_counts[PatientStatus.IN_TREATMENT]}")
    print(f"Completed count: {status_counts[PatientStatus.COMPLETED]}")
    print(f"Referred count: {status_counts[PatientStatus.REFERRED]}")


if __name__ == "__main__":
    main()
